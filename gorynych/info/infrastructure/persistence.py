'''
Realization of persistence logic.
'''
import simplejson as json

from twisted.internet import defer
from zope.interface import implements, implementer
import psycopg2

from gorynych.info.domain.contest import Paraglider, IContestRepository, ContestFactory
from gorynych.info.domain.ids import PersonID
from gorynych.info.domain.race import IRaceRepository, RaceFactory
from gorynych.common.domain.types import checkpoint_collection_from_geojson, geojson_feature_collection, Name
from gorynych.info.domain.person import IPersonRepository, PersonFactory
from gorynych.common.exceptions import NoAggregate, DatabaseValueError
from gorynych.common.infrastructure import persistence as pe
from gorynych.info.domain import interfaces
from gorynych.info.domain.tracker import TrackerFactory


def create_participants(paragliders_row):
    result = dict()
    if paragliders_row:
        result = list()
        for tup in paragliders_row:
            _id, pid, cn, co, gl, ti, n, sn = tup
            result.append(Paraglider(pid, Name(n, sn), co,
                gl, cn, ti))
    return result

# TODO: simplify repositories.

@implementer(interfaces.IRepository)
class BasePGSQLRepository(object):
    def __init__(self, pool):
        self.pool = pool
        self.name = self.__class__.__name__[5:-10].lower()

    @defer.inlineCallbacks
    def get_list(self, limit=20, offset=None):
        idname = self.name + '_id'
        result = []
        command = ' '.join(('select', idname, 'from', self.name))
        if limit:
            command += ' limit ' + str(limit)
        if offset:
            command += ' offset ' + str(offset)
        ids = yield self.pool.runQuery(command)
        for idx, pid in enumerate(ids):
            item = yield self.get_by_id(pid[0])
            result.append(item)
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
                result = yield self._get_existed(obj)
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
                if e.pgcode == '23505':
                    pid = yield self.pool.runQuery(pe.select('by_email',
                        'person'), (str(pers.email),))
                    result = yield self.get_by_id(pid[0][0])
                    defer.returnValue(result)
            result = yield self._process_insert_result(data, pers)
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
        chs = checkpoint_collection_from_geojson(_chs)

        if _aux:
            aux = json.loads(_aux)
            b = aux.get('bearing')
        else:
            b = None
        factory = RaceFactory()
        result = factory.create_race(t, rt, tz, ps, chs, race_id=rid,
            bearing=b, timelimits=(slt, elt))
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
            return x

        def update(cur, pgs):
            cur.execute(pe.update('race'), values['race'])

            inobj = values['paragliders']
            indb = pgs
            for idx, p in enumerate(inobj):
                p.insert(0, obj._id)
                inobj[idx] = tuple(p)
            to_insert = set(inobj).difference(set(indb))
            to_delete = set(indb).difference(set(inobj))
            if to_delete:
                ids = tuple([x[1] for x in to_delete])
                cur.execute("DELETE FROM paraglider WHERE id=%s "
                            "AND person_id in %s", (obj._id, ids))
            if to_insert:
                q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s)",
                    (pitem)) for pitem in to_insert)
                cur.execute("INSERT into paraglider values " + q)
            return obj


        if obj._id:
            pgs = yield self.pool.runQuery(pe.select('paragliders', 'race'),
                (obj._id,))
            if not pgs:
                raise DatabaseValueError(
                    "No paragliders has been found for race %s." % obj.id)
            result = yield self.pool.runInteraction(update, pgs)
        else:
            r_id = yield self.pool.runInteraction(save_new)
            obj._id = r_id[0]
            result = obj
        defer.returnValue(result)

    def _get_values_from_obj(self, obj):
        result = dict()
        bearing = ''
        if obj.type == 'opendistance':
            if obj.task.bearing is None:
                raise ValueError("Race don't have bearing.")
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
                    p.country, p.glider, p.tracker_id,
                    p._name.name, p._name.surname])
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
    def _restore_aggregate(self, row):
        factory = TrackerFactory()
        did, dtype, name, tid, assignee, _id = row
        result = factory.create_tracker(device_id=did, device_type=dtype,
            name=name, assignee=assignee)
        result._id = _id
        return result

    # TODO: generalize this.
    def _save_new(self, obj):
        return self.pool.runQuery(pe.insert('tracker'),
                                                self._extract_sql_fields(obj))

    # TODO: generalize this.
    def _update(self, obj):
        return self.pool.runOperation(pe.update('tracker'),
            self._extract_sql_fields(obj))


    def _extract_sql_fields(self, obj):
        '''

        @param obj:
        @type obj: gorynych.info.domain.tracker.Tracker
        @return:
        @rtype:
        '''
        return (obj.device_id, obj.device_type, obj.name,
                str(obj.assignee), str(obj.id))

    def _get_existed(self, obj):
        pass