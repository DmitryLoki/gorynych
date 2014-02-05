'''
Realization of persistence logic.
'''
import simplejson as json
import collections

from twisted.internet import defer
from twisted.python import log
from zope.interface import implementer
import psycopg2

from gorynych.common.domain.types import checkpoint_collection_from_geojson, geojson_feature_collection, Name
from gorynych.common.exceptions import NoAggregate, DatabaseValueError
from gorynych.common.infrastructure import persistence as pe
from gorynych.info.domain import interfaces, contest, race, person, tracker
from gorynych.info.domain import ids, transport
from gorynych.info.domain.transport import TransportFactory


def create_participants(paragliders_row):
    result = dict()
    if paragliders_row:
        result = list()
        for tup in paragliders_row:
            _id, pid, cn, co, gl, ti, n, sn = tup
            result.append(race.Paraglider(pid, Name(n, sn), co, gl, cn, ti))
    return result


def find_delete_insert(indb, inobj, _id):
    for idx, p in enumerate(inobj):
        p.insert(0, _id)
        inobj[idx] = tuple(p)
    to_insert = set(inobj).difference(set(indb))
    to_delete = set(indb).difference(set(inobj))
    return to_delete, to_insert


@implementer(interfaces.IRepository)
class BasePGSQLRepository(object):
    use_events = True
    has_many = []
    factory = None

    def __init__(self, pool):
        self.pool = pool
        self.name = self.__class__.__name__[5:-10].lower()

    @defer.inlineCallbacks
    def get_by_id(self, id):
        data = yield self.pool.runQuery(pe.select(self.name), (str(id),))
        if not data:
            raise NoAggregate("%s %s" % (self.name.title(), id))
        aggr_collections = dict()
        if self.has_many:
            for tblname in self.has_many:
                rows = yield self.pool.runQuery(pe.select(tblname, self.name),
                    (data[0][0],))
                aggr_collections[tblname] = rows

        result = yield defer.maybeDeferred(self._restore_aggregate, data[0],
            aggr_collections)
        if self.use_events:
            event_list = yield defer.maybeDeferred(pe.event_store().load_events,
                result.id)
            result.apply(event_list)
        result._id = long(data[0][0])
        defer.returnValue(result)

    def _restore_aggregate(self, row, aggr_collections):
        '''
        Method restore aggregate and prepare aggregate's objects collections
        for factory.restore method.
        Collections names are defined in self.has_many list.
        @param row: row for aggregate from DB.
        @type row: C{tuple}
        @param aggr_collections: collections of loaded from participant or
        task DB-rows. Dictionary with tablenames as a key and list of rows.
        @type aggr_collections: C{dict}
        @return:
        @rtype: C{Deferred}
        '''
        result = self.factory.create(*self._read_aggregate_row(row[1:]))
        collections_dict = {x: None for x in self.has_many}
        for tblname in self.has_many:
            if tblname in aggr_collections:
                columns = getattr(self, tblname + '_columns')
                try:
                    collections_dict[tblname] = [
                        pe.named_row(columns)(*row) for row in
                        aggr_collections[tblname]]
                except TypeError as e:
                    print '>'*8
                    print tblname
                    print len(row), row
                    print '>'*8
                    raise e
        result = self.factory.restore(result, **collections_dict)
        return result

    def _read_aggregate_row(self, row):
        '''
            Read and reorder row from DB to factory parameters if necessary
            @param row: raw row from DB
            @type row: C{tuple}
            @return: list with parameters for create() factory method.
            @rtype: C{list}
            '''
        return row

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
    def save(self, obj):
        try:
            if obj._id:
                yield self._update(obj._id, self._read_aggregate(obj))
                result = obj
            else:
                _id = yield self._save_new(self._read_aggregate(obj))
                obj._id = _id[0][0]
                result = obj
        except psycopg2.IntegrityError as e:
            if e.pgcode == '23505':
                # unique constraints violation
                result = yield self._get_existed(obj, e)
                defer.returnValue(result)
        defer.returnValue(result)

    def _read_aggregate(self, aggr):
        '''
            Read data from aggregate and return it for inserting.
            '''
        raise NotImplementedError()


@implementer(interfaces.IPersonRepository)
class PGSQLPersonRepository(BasePGSQLRepository):
    def _restore_aggregate(self, data_row):
        if data_row:
            # regdate is datetime.datetime object
            regdate = data_row[4]
            factory = person.PersonFactory()
            result = factory.create_person(data_row[0], data_row[1],
                data_row[2], data_row[3], data_row[5])
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
                    pid = yield self.pool.runQuery(
                        pe.select('by_email', 'person'), (str(pers.email),))
                    result = yield self.get_by_id(pid[0][0])
                    defer.returnValue(result)
            result = yield self._process_insert_result(data, pers)

        if pers._person_data:
            yield self._insert_person_data(pers)

        defer.returnValue(result)

    def _extract_sql_fields(self, pers=None):
        if pers is None:
            return ()
        return (pers.name.name, pers.name.surname, pers.regdate, pers.country,
        pers.email, str(pers.id))

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
                    (pers._id, data_type, data_value))
            except psycopg2.IntegrityError as e:
                if e.pgcode == '23505':   # unique constraint
                    # or replace it with error if persistence is needed
                    log.msg("Error occured while inserting %s, %s, %s" % (
                        data_value, pers._id, data_type
                    ))
                    try:
                        yield self.pool.runOperation(pe.update('person_data', 'person'),
                            (data_value, pers._id, data_type))
                    except Exception as error:
                        log.msg("Pizdec occured while updating %r" % error)
                else:
                    log.err("Error occured with code %s: %r" % (e.pgcode, e))


@implementer(interfaces.IRaceRepository)
class PGSQLRaceRepository(BasePGSQLRepository):
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
        factory = race.RaceFactory()
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
        to_delete_pg, to_insert_pg = find_delete_insert(pgs,
            values['paragliders'], obj._id)
        if to_delete_pg:
            ids = tuple([x[1] for x in to_delete_pg])
            cur.execute("DELETE FROM paraglider WHERE id=%s "
                        "AND person_id in %s", (obj._id, ids))
        if to_insert_pg:
            q = ','.join(
                cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s)", (pitem)) for
                    pitem in to_insert_pg)
            cur.execute("INSERT INTO paraglider VALUES " + q)

        # Update transport. Should it be in a separate general method/func?
        to_delete_tr, to_insert_tr = find_delete_insert(trs, values['transport'], obj._id)
        if to_delete_tr:
            ids = tuple([x[1] for x in to_delete_tr])
            cur.execute("DELETE FROM race_transport WHERE id=%s AND "
                        "transport_id in %s", (obj._id, ids))
        if to_insert_tr:
            q = ','.join(
                cur.mogrify("(%s, %s, %s, %s, %s, %s)", (pitem)) for pitem in
                    to_insert_tr)
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
                bearing = None
            else:
                bearing = json.dumps(dict(bearing=int(obj.task.bearing)))
        result['race'] = (
            obj.title, obj.start_time, obj.end_time, obj.timezone, obj.type,
        geojson_feature_collection(obj.checkpoints), bearing, obj.timelimits[0], obj.timelimits[1],
            str(obj.id))
        result['paragliders'] = []
        for key in obj.paragliders:
            p = obj.paragliders[key]
            result['paragliders'].append(
                [str(p.person_id), str(p.contest_number), p.country, p.glider,
                    str(p.tracker_id) if p.tracker_id else '', p._name.name, p._name.surname])
        result['transport'] = []
        for item in obj.transport:
            result['transport'].append(
                [str(item['transport_id']), item['description'], item['title'],
                    str(item['tracker_id']), item['type']])
        result['organizers'] = []
        return result


@implementer(interfaces.IContestRepository)
class PGSQLContestRepository(BasePGSQLRepository):
    use_events = False
    has_many = ['participants', 'tasks']
    factory = contest.ContestFactory()

    participants_columns = ['id', 'pid', 'role', 'glider', 'contest_number',
        'description', 'type', 'phone', 'name', 'email', 'country', 'title']
    tasks_columns = ['id', 'task_id', 'type', 'title', 'window_open',
        'deadline', 'window_close', 'start_time', 'checkpoints', 'bearing',
        'gates_number', 'gates_interval']

    def _save_new(self, values):
        def save_new(cur):
            '''
            Save just created contest.
            '''
            i = cur.execute(pe.insert('contest'), values['contest'])
            _id = cur.fetchone()[0]
            if values['participants']:
                rows = [x.appendleft(_id) for x in values['participants']]
                cur.executemany(pe.insert('participant', 'contest'), rows)

            return [[_id]]

        return self.pool.runInteraction(save_new)

    @defer.inlineCallbacks
    def _update(self, _id, values):
        prts = yield self.pool.runQuery(pe.select('participants', 'contest'),
            (_id,))

        def update(cur, prts):
            cur.execute(pe.update('contest'), values['contest'])
            if values['participants'] or prts:
                # inobj = values['participants']
                indb = prts
                inobj = [tuple(*p.appendleft(_id)) for p in
                    values['participants']]
                # for idx, p in enumerate(inobj):
                #     p.appendleft(_id)
                #     inobj[idx] = tuple(p)
                to_insert = set(inobj).difference(set(indb))
                to_delete = set(indb).difference(set(inobj))
                if to_delete:
                    ids = tuple([x[1] for x in to_delete])
                    cur.execute("DELETE FROM participant WHERE id=%s "
                                "AND participant_id in %s", (_id, ids))
                if to_insert:
                    cur.executemany(pe.insert('participant', 'contest'),
                        to_insert)

        yield self.pool.runInteraction(update, prts)


    # @defer.inlineCallbacks
    # def save(self, obj):
    #     values = self._read_aggregate(obj)
    #
    #     def insert_id(_id, _list):
    #         _list.insert(0, _id)
    #         return _list
    #
    #     # def save_new(cur):
    #     #     '''
    #     #     Save just created contest.
    #     #     '''
    #     #
    #     #     i = cur.execute(pe.insert('contest'), values['contest'])
    #     #     _id = cur.fetchone()[0]
    #     #
    #     #     if values['participants']:
    #     #         # Callbacks wan't work in for loop, so i insert multiple values
    #     #         # in one query.
    #     #         # Oh yes, executemany also wan't work in asynchronous mode.
    #     #         q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)",
    #     #             (insert_id(_id, p))) for p in values['participants'])
    #     #         cur.execute("INSERT into participant values " + q)
    #     #     cur.execute("INSERT INTO contest_retrieve_id values (%s, %s)",
    #     #         (_id, obj.retrieve_id))
    #     #
    #     #     return _id
    #     #
    #     # # def update(cur, prts):
    #     # #     cur.execute(pe.update('contest'), values['contest'])
    #     # #     if values['participants'] or prts:
    #     # #         inobj = values['participants']
    #     # #         indb = prts
    #     # #         for idx, p in enumerate(inobj):
    #     # #             p.insert(0, obj._id)
    #     # #             inobj[idx] = tuple(p)
    #     # #         to_insert = set(inobj).difference(set(indb))
    #     # #         to_delete = set(indb).difference(set(inobj))
    #     # #         if to_delete:
    #     # #             ids = tuple([x[1] for x in to_delete])
    #     # #             cur.execute("DELETE FROM participant WHERE id=%s "
    #     # #                         "AND participant_id in %s", (obj._id, ids))
    #     # #         if to_insert:
    #     # #             q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)",
    #     # #                 (pitem)) for pitem in to_insert)
    #     # #             cur.execute("INSERT into participant values " + q)
    #     # #     if obj.retrieve_id:
    #     # #         cur.execute(
    #     # #             "UPDATE contest_retrieve_id SET retrieve_id=%s where"
    #     # #                     " id=%s", (obj.retrieve_id, obj._id))
    #     # #
    #     # #     return obj
    #     #
    #     # # if obj._id:
    #     # #     prts = yield self.pool.runQuery(pe.select('participants',
    #     # #         'contest'), (obj._id,))
    #     # #     result = yield self.pool.runInteraction(update, prts)
    #     # # else:
    #     # #     c__id = yield self.pool.runInteraction(save_new)
    #     # #     obj._id = c__id
    #     # #     result = obj
    #     # # defer.returnValue(result)

    def _read_aggregate(self, obj):
        '''

        @param obj:
        @type obj: L{gorynych.info.domain.contest.Contest}
        @return:
        @rtype:
        '''
        result = dict()
        result['contest'] = (
            obj.title, obj.start_time, obj.end_time, obj.timezone, obj.address.place, obj.address.country,
            obj.address.lat, obj.address.lon, str(obj.retrieve_id), str(obj.id))

        # Extract participants.
        result['participants'] = []
        for role in ['organizers', 'paragliders', 'winddummies', 'staff']:
            rows = self._read_participants(getattr(obj, role))
            map(result['participants'].append, rows)
        return result

    def _read_participants(self, collection):
        '''
        Read collection with participants and return tuples for inserting.
        @param collection: collection with contest's participants.
        @type collection: L{gorynych.common.domain.types.MappingCollection}
        @return: list of deques for inserting.
        @rtype: C{list}
        '''
        result = []
        for val in collection.itervalues():
            def get(name, obj=val):
                res = getattr(obj, name, '')
                if callable(res):
                    return res()
                return res

            # TODO: do typecast in psycopg2?
            row = collections.deque(
                [str(val.id), val.__class__.__name__.lower(), get('glider'),
                    str(get('contest_number')), get('description'), get('type'), get('number', get('phone')),
                    get('full', get('name')), get('email'), get('code', get('country')),
                    get('title')])
            result.append(row)
        return result


@implementer(interfaces.ITrackerRepository)
class PGSQLTrackerRepository(BasePGSQLRepository):
    @defer.inlineCallbacks
    def _restore_aggregate(self, row):
        factory = tracker.TrackerFactory()
        did, dtype, tid, name, _id = row
        last_point = yield self.pool.runQuery(pe.select('last_point', 'tracker'), (_id,))
        if last_point:
            last_point = last_point[0]
        assignee = yield self._get_assignee(_id)
        result = factory.create_tracker(device_id=did, device_type=dtype,
            name=name, assignee=assignee, last_point=last_point)
        result._id = _id
        defer.returnValue(result)

    # TODO: generalize this.
    def _save_new(self, row):
        return self.pool.runQuery(pe.insert('tracker'), row[:-1])

    @defer.inlineCallbacks
    def _update(self, _id, row):
        ass = yield self._get_assignee(_id)
        if ass == row[-1]:
            yield self.pool.runOperation(pe.update('tracker'), row[:-1])
            defer.returnValue('')

        # something has been changed in assignees
        to_insert = set(row[-1].viewitems()).difference(set(ass.items()))
        to_delete = set(ass.items()).difference(set(row[-1].viewitems()))

        def update(cur):
            cur.execute(pe.update('tracker'), row[:-1])
            for ditem in to_delete:
                cur.execute('DELETE FROM tracker_assignees WHERE id=%s AND '
                            'assignee_id=%s and assigned_for=%s',
                    (_id, ditem[1], ditem[0]))
            for item in to_insert:
                cur.execute('INSERT INTO tracker_assignees VALUES(%s, %s, '
                            '%s)', (_id, str(item[1]), str(item[0])))

        yield self.pool.runInteraction(update)

    @defer.inlineCallbacks
    def _get_assignee(self, _id):
        ass = yield self.pool.runQuery(pe.select('assignee', 'tracker'), (_id,
        ))
        assignee = dict()
        for item in ass:
            assignee[item[1]] = item[0]
        defer.returnValue(assignee)

    def _read_aggregate(self, obj):
        '''

        @param obj:
        @type obj: gorynych.info.domain.tracker.Tracker
        @return:
        @rtype:
        '''
        return obj.device_id, obj.device_type, obj.name, str(obj.id), obj.assignee

    def _get_existed(self, obj, e):
        return self.get_by_id(obj.id)


@implementer(interfaces.ITransportRepository)
class PGSQLTransportRepository(BasePGSQLRepository):
    def _restore_aggregate(self, rows):
        factory = TransportFactory()
        _id, _tid, _title, _ttype, _desc = rows
        result = factory.create_transport(_ttype, _title, _desc, tr_id=_tid)
        result._id = _id
        return result

    def _save_new(self, row):
        return self.pool.runQuery(pe.insert('transport'), row)

    def _update(self, _id, row):
        return self.pool.runOperation(pe.update('transport'), row)

    def _read_aggregate(self, obj):
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

