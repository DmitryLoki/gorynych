'''
Realization of persistence logic.
'''
import simplejson as json

from twisted.internet import defer
from twisted.python import log
from zope.interface import implements, implementer
import psycopg2

from gorynych.info.domain.contest import Paraglider, IContestRepository, ContestFactory
from gorynych.info.domain.ids import PersonID, TransportID
from gorynych.info.domain.race import IRaceRepository, RaceFactory
from gorynych.common.domain.types import checkpoint_collection_from_geojson, geojson_feature_collection, Name
from gorynych.info.domain.person import IPersonRepository, PersonFactory
from gorynych.common.exceptions import NoAggregate, DatabaseValueError
from gorynych.common.infrastructure import persistence as pe
from gorynych.info.domain import interfaces
from gorynych.info.domain.tracker import TrackerFactory
from gorynych.info.domain.transport import TransportFactory


def create_participants(paragliders_row):
    result = dict()
    if paragliders_row:
        result = list()
        for tup in paragliders_row:
            _id, pid, cn, co, gl, ti, n, sn = tup
            result.append(Paraglider(pid, Name(n, sn), co,
                gl, cn, ti))
    return result


def find_delete_insert(indb, inobj, _id):
    for idx, p in enumerate(inobj):
        p.insert(0, _id)
        inobj[idx] = tuple(p)
    to_insert = set(inobj).difference(set(indb))
    to_delete = set(indb).difference(set(inobj))
    return to_delete, to_insert


# TODO: simplify repositories.

@implementer(interfaces.IRepository)
class BasePGSQLRepository(object):
    def __init__(self, pool):
        self.pool = pool
        self.name = self.__class__.__name__[5:-10].lower()

    @defer.inlineCallbacks
    def get_list(self, limit=20, offset=None):
        name = 'all_' + self.name
        rows = yield self.pool.runQuery(pe.select(name, self.name))
        a_ids = [row[0] for row in rows]
        event_dict = yield pe.event_store().load_events_for_aggregates(a_ids)
        result = yield self._restore_aggregates(rows)
        for key in result:
            if event_dict.get(key):
                result[key].apply(event_dict[key])
        defer.returnValue(result.values())

    @defer.inlineCallbacks
    def _restore_aggregates(self, rows):
        result = dict()
        for row in rows:
            result[row[0]] = yield self._restore_aggregate(row[1:])
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_by_id(self, id):
        data = yield self.pool.runQuery(pe.select(self.name), (str(id),))
        if not data:
            raise NoAggregate("%s %s" % (self.name.title(), id))
        result = yield defer.maybeDeferred(self._restore_aggregate, data[0])
        event_list = yield pe.event_store().load_events(result.id)
        result.apply(event_list)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def save(self, obj):
        result = None
        try:
            if obj._id:
                yield self._update(obj)
                result = obj
            else:
                _id = yield self._save_new(obj)
                obj._id = _id[0][0]
                result = obj
        except psycopg2.IntegrityError as e:
            if e.pgcode == '23505':
                # unique constraints violation
                result = yield self._get_existed(obj, e)
                defer.returnValue(result)
        defer.returnValue(result)


class PGSQLPersonRepository(BasePGSQLRepository):
    implements(IPersonRepository)

    def _restore_aggregate(self, data_row):
        if data_row:
            # regdate is datetime.datetime object
            regdate = data_row[4]
            factory = PersonFactory()
            result = factory.create_person(
                data_row[0],
                data_row[1],
                data_row[2],
                data_row[3],
                regdate.year,
                regdate.month,
                regdate.day,
                data_row[5])
            result._id = data_row[6]
            return result

    @defer.inlineCallbacks
    def save(self, pers):
        if pers._id:
            yield self.pool.runOperation(pe.update('person'),
                self._extract_sql_fields(pers))
            result = pers
        else:
            try:
                data = yield self.pool.runQuery(pe.insert('person'),
                    self._extract_sql_fields(pers))
            except psycopg2.IntegrityError as e:
                if e.pgcode == '23505':   # unique constraint
                    pid = yield self.pool.runQuery(pe.select('by_email',
                        'person'), (str(pers.email),))
                    result = yield self.get_by_id(pid[0][0])
                    defer.returnValue(result)
            result = yield self._process_insert_result(data, pers)

        if pers._person_data:
            yield self._insert_person_data(pers)

        defer.returnValue(result)

    def _extract_sql_fields(self, pers=None):
        if pers is None:
            return ()
        return (pers.name.name, pers.name.surname, pers.regdate,
        pers.country, pers.email, str(pers.id))

    def _process_insert_result(self, data, pers):
        if data is not None and pers is not None:
            inserted_id = data[0][0]
            pers._id = inserted_id
            return pers
        return None

    @defer.inlineCallbacks
    def _insert_person_data(self, pers):
        for data_type, data_value in pers._person_data.iteritems():
            try:
                yield self.pool.runOperation(
                    pe.insert('person_data', 'person'),
                                             (pers._id, data_type,
                                              data_value))
            except psycopg2.IntegrityError as e:
                if e.pgcode == '23505':   # unique constraint
                    # or replace it with error if persistence is needed
                    yield self.pool.runOperation(
                        pe.update('person_data', 'person'),
                                                 (data_value, pers._id,
                                                  data_type))


class PGSQLRaceRepository(BasePGSQLRepository):
    implements(IRaceRepository)

    @defer.inlineCallbacks
    def _restore_aggregate(self, race_data):
        # TODO: repository knows too much about Race's internals. Think about it
        i, rid, t, st, et, tz, rt, _chs, _aux, slt, elt = race_data

        pgs = yield self.pool.runQuery(pe.select('paragliders', 'race'),
            (race_data[0],))
        if not pgs:
            raise DatabaseValueError("No paragliders has been found for race"
                                     " %s." % race_data[1])
        ps = create_participants(pgs)

        trs = yield self.pool.runQuery(pe.select('race_transport', 'race'),
            (rid,))

        chs = checkpoint_collection_from_geojson(_chs)

        if _aux:
            aux = json.loads(_aux)
            b = aux.get('bearing')
        else:
            b = None
        factory = RaceFactory()
        result = factory.create_race(t, rt, tz, ps, chs, race_id=rid,
            transport=trs, bearing=b, timelimits=(slt, elt))
        result._start_time = st
        result._end_time = et
        result._id = long(i)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def save(self, obj):
        result = []
        values = self._get_values_from_obj(obj)

        def insert_id(_id, _list):
            _list.insert(0, _id)
            return _list

        def save_new(cur):
            cur.execute(pe.insert('race'), values['race'])
            x = cur.fetchone()
            pq = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s)",
                (insert_id(x[0], p))) for p in values['paragliders'])
            cur.execute("INSERT INTO paraglider VALUES " + pq)
            if values['transport']:
                tr = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s)",
                    (insert_id(x[0], p))) for p in values['transport'])
                cur.execute("INSERT INTO race_transport VALUES" + tr)
            if values['organizers']:
                pass
            return x

        if obj._id:
            pgs = yield self.pool.runQuery(pe.select('paragliders', 'race'),
                (obj._id,))
            if not pgs:
                raise DatabaseValueError(
                    "No paragliders has been found for race %s." % obj.id)
            trs = yield self.pool.runQuery(pe.select('transport', 'race'),
                (obj._id,))
            result = yield self.pool.runInteraction(self._update, pgs, trs,
                values, obj)
        else:
            r_id = yield self.pool.runInteraction(save_new)
            obj._id = r_id[0]
            result = obj
        defer.returnValue(result)

    def _update(self, cur, pgs, trs, values, obj):
        '''

        @param cur:
        @type cur:
        @param pgs: [(id, pers_id, cnumber, country, glider, tr_id, name,
        sn),]
        @type pgs: list
        @param trs: [(id, transport_id, description, title, tracker_id),]
        @type trs: list
        @param values:
        @type values: dict
        @param obj:
        @type obj:
        @return: obj
        @rtype:
        '''
        cur.execute(pe.update('race'), values['race'])

        # Update paragliders. Should it be in a separate method/function?
        to_delete_pg, to_insert_pg = find_delete_insert(
                                pgs, values['paragliders'], obj._id)
        if to_delete_pg:
            ids = tuple([x[1] for x in to_delete_pg])
            cur.execute("DELETE FROM paraglider WHERE id=%s "
                        "AND person_id in %s", (obj._id, ids))
        if to_insert_pg:
            q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s)",
                (pitem)) for pitem in to_insert_pg)
            cur.execute("INSERT into paraglider values " + q)

        # Update transport. Should it be in a separate general method/func?
        to_delete_tr, to_insert_tr = find_delete_insert(
                                trs, values['transport'], obj._id)
        if to_delete_tr:
            ids = tuple([x[1] for x in to_delete_tr])
            cur.execute("DELETE FROM race_transport WHERE id=%s AND "
                        "transport_id in %s", (obj._id, ids))
        if to_insert_tr:
            q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s)",
                (pitem)) for pitem in to_insert_tr)
            cur.execute("INSERT INTO race_transport VALUES " + q)
        return obj

    def _get_values_from_obj(self, obj):
        '''

        @param obj:
        @type obj: gorynych.info.domain.race.Race
        @return:
        @rtype:
        '''
        result = dict()
        bearing = ''
        if obj.type == 'opendistance':
            if obj.task.bearing is None:
                raise ValueError("Race doesn't have a bearing.")
            bearing = json.dumps(dict(bearing=int(obj.task.bearing)))
        result['race'] = (obj.title, obj.start_time, obj.end_time,
        obj.timezone, obj.type,
        geojson_feature_collection(obj.checkpoints),
        bearing, obj.timelimits[0], obj.timelimits[1],
        str(obj.id))
        result['paragliders'] = []
        for key in obj.paragliders:
            p = obj.paragliders[key]
            result['paragliders'].append(
                [str(p.person_id), str(p.contest_number),
                    p.country, p.glider,
                    str(p.tracker_id) if p.tracker_id else '',
                    p._name.name, p._name.surname])
        result['transport'] = []
        for item in obj.transport:
            result['transport'].append([str(item['transport_id']),
                item['description'], item['title'], str(item['tracker_id']),
                item['type']])
        result['organizers'] = []
        return result


class PGSQLContestRepository(BasePGSQLRepository):
    implements(IContestRepository)

    @defer.inlineCallbacks
    def _append_data_to_contest(self, cont):
        participants = yield self.pool.runQuery(
            pe.select('participants', 'contest'), (cont._id,))
        if participants:
            cont = self._add_participants_to_contest(cont, participants)
        defer.returnValue(cont)

    @defer.inlineCallbacks
    def _restore_aggregate(self, row):
        '''

        @param row: (id, contest_id, title, stime, etime, tz, place,
        country, hq_lat, hq_lon)
        @type row: C{tuple}
        @return: contest
        @rtype: C{Contest}
        '''
        factory = ContestFactory()
        sid, cid, ti, st, et, tz, pl, co, lat, lon = row
        cont = factory.create_contest(ti, st, et, pl, co, (lat, lon), tz, cid)
        cont._id = sid
        cont = yield self._append_data_to_contest(cont)
        defer.returnValue(cont)

    def _add_participants_to_contest(self, cont, rows):
        '''

        @param cont:
        @type cont: C{Contest}
        @param rows: [(id, participant_id, role, glider,
        contest_number, description, type)]
        @type rows: C{list}
        @return:
        @rtype:
        '''
        participants = dict()
        for row in rows:
            id, pid, role, glider, cnum, desc, ptype = row
            if role == 'paraglider':
                participants[PersonID.fromstring(pid)] = dict(
                    role=role,
                    contest_number=cnum,
                    glider=str(glider))
            elif role == 'organizator':
                participants[PersonID.fromstring(pid)] = dict(role=role)
            elif role == 'transport':
                participants[TransportID.fromstring(pid)] = dict(role=role)
        cont._participants = participants
        return cont

    @defer.inlineCallbacks
    def save(self, obj):
        values = self._extract_values_from_contest(obj)

        def insert_id(_id, _list):
            _list.insert(0, _id)
            return _list

        def save_new(cur):
            '''
            Save just created contest.
            '''

            i = cur.execute(pe.insert('contest'), values['contest'])
            x = cur.fetchone()

            if values['participants']:
                # Callbacks wan't work in for loop, so i insert multiple values
                # in one query.
                # Oh yes, executemany also wan't work in asynchronous mode.
                q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)",
                    (insert_id(x[0], p))) for p in values['participants'])
                cur.execute("INSERT into participant values " + q)

            return x

        def update(cur, prts):
            cur.execute(pe.update('contest'), values['contest'])
            if values['participants'] or prts:
                inobj = values['participants']
                indb = prts
                for idx, p in enumerate(inobj):
                    p.insert(0, obj._id)
                    inobj[idx] = tuple(p)
                to_insert = set(inobj).difference(set(indb))
                to_delete = set(indb).difference(set(inobj))
                if to_delete:
                    ids = tuple([x[1] for x in to_delete])
                    cur.execute("DELETE FROM participant WHERE id=%s "
                                "AND participant_id in %s", (obj._id, ids))
                if to_insert:
                    q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)",
                        (pitem)) for pitem in to_insert)
                    cur.execute("INSERT into participant values " + q)

            return obj

        result = None
        if obj._id:
            prts = yield self.pool.runQuery(pe.select('participants',
                'contest'), (obj._id,))
            result = yield self.pool.runInteraction(update, prts)
        else:
            c__id = yield self.pool.runInteraction(save_new)
            obj._id = c__id[0]
            result = obj
        defer.returnValue(result)

    def _extract_values_from_contest(self, obj):
        result = dict()
        result['contest'] = (obj.title, obj.start_time, obj.end_time,
        obj.timezone,
        obj.address.place, obj.address.country,
        obj.address.lat, obj.address.lon, str(obj.id))

        result['participants'] = []
        for key in obj._participants:
            p = obj._participants[key]
            row = [str(key), p['role'], p.get('glider', ''),
                p.get('contest_number', ''), p.get('description', ''),
                key.__class__.__name__.lower()[:-2]]
            result['participants'].append(row)

        return result


@implementer(interfaces.ITrackerRepository)
class PGSQLTrackerRepository(BasePGSQLRepository):
    @defer.inlineCallbacks
    def _restore_aggregate(self, row):
        factory = TrackerFactory()
        did, dtype, tid, name, _id = row
        last_point = yield self.pool.runQuery(pe.select('last_point',
            'tracker'), (_id,))
        if last_point:
            last_point=last_point[0]
        assignee = yield self._get_assignee(_id)
        result = factory.create_tracker(device_id=did, device_type=dtype,
            name=name, assignee=assignee, last_point=last_point)
        result._id = _id
        defer.returnValue(result)

    # TODO: generalize this.
    def _save_new(self, obj):
        return self.pool.runQuery(pe.insert('tracker'),
                                                self._extract_sql_fields(obj))

    @defer.inlineCallbacks
    def _update(self, obj):
        ass = yield self._get_assignee(obj._id)
        if ass == obj.assignee:
            yield self.pool.runOperation(pe.update('tracker'),
                self._extract_sql_fields(obj))
            defer.returnValue('')

        # something has been changed in assignees
        to_insert = set(obj.assignee.viewitems()).difference(set(ass))
        to_delete = set(ass).difference(set(obj.assignee.viewitems()))

        def update(cur):
            cur.execute(pe.update('tracker'), self._extract_sql_fields(obj))
            for ditem in to_delete:
                cur.execute('delete from tracker_assignees where id=%s and '
                            'assignee_id=%s and assigned_for=%s',
                    (obj._id, ditem[1], ditem[0]))
            for item in to_insert:
                cur.execute('insert into tracker_assignees values(%s, %s, '
                            '%s)', (obj._id, str(item[1]), str(item[0])))

        yield self.pool.runInteraction(update)

    @defer.inlineCallbacks
    def _get_assignee(self, _id):
        ass = yield self.pool.runQuery(pe.select('assignee', 'tracker'), (_id,
        ))
        assignee = dict()
        for item in ass:
            assignee[item[1]]=item[0]
        defer.returnValue(assignee)


    def _extract_sql_fields(self, obj):
        '''

        @param obj:
        @type obj: gorynych.info.domain.tracker.Tracker
        @return:
        @rtype:
        '''
        return obj.device_id, obj.device_type, obj.name, str(obj.id)

    def _get_existed(self, obj, e):
        return self.get_by_id(obj.id)


@implementer(interfaces.ITransportRepository)
class PGSQLTransportRepository(BasePGSQLRepository):

    def _restore_aggregate(self, rows):
        factory = TransportFactory()
        _id, _tid, _title, _ttype, _desc = rows
        result = factory.create_transport( _ttype, _title, _desc, tr_id=_tid)
        result._id = _id
        return result

    def _save_new(self, obj):
        return self.pool.runQuery(pe.insert('transport'),
            self._extract_sql_fields(obj))

    def _update(self, obj):
        return self.pool.runOperation(pe.update('transport'),
            self._extract_sql_fields(obj))

    def _extract_sql_fields(self, obj):
        '''

        @param obj:
        @type obj: gorynych.info.domain.transport.Transport
        @return:
        @rtype: tuple
        '''
        a = (obj.title, obj.type, obj.description, str(obj.id))
        return a

    def _get_existed(self, obj, e):
        return self.get_by_id(obj.id)
