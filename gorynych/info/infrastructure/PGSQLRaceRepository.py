from twisted.internet import defer
from zope.interface import implements

from gorynych.info.domain.race import IRaceRepository, RaceFactory
from gorynych.info.domain.contest import Paraglider
from gorynych.common.exceptions import NoAggregate, DatabaseValueError
from gorynych.common.domain.types import geojson_feature_collection, checkpoint_collection_from_geojson, Name
from gorynych.common.infrastructure import persistence as pe


def create_participants(paragliders_row):
    result = dict()
    if paragliders_row:
        result['paragliders'] = dict()
        for tup in paragliders_row:
            _id, pid, cn , co, gl, ti, n, sn = tup
            result['paragliders'][cn] = Paraglider(pid, Name(n, sn), co,
                                                   gl, cn, ti)
    return result


class PGSQLRaceRepository(object):
    implements(IRaceRepository)

    def __init__(self, pool):
        self.pool = pool
        self.factory = RaceFactory()

    @defer.inlineCallbacks
    def get_list(self, limit=20, offset=None):
        result = []
        command = "select id from race"
        if limit:
            command += ' limit ' + str(limit)
        if offset:
            command += ' offset ' + str(offset)
        ids = yield self.pool.runQuery(command)
        for idx, rid in enumerate(ids):
            rc = yield self.get_by_id(rid[0])
            result.append(rc)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_by_id(self, race_id):
        race_data = yield self.pool.runQuery(pe.select('race'), (str(race_id),))
        if not race_data:
            raise NoAggregate("Race")

        pgs = yield self.pool.runQuery(pe.select('paragliders', 'race'),
                                       (race_data[0][0],))
        if not pgs:
            raise DatabaseValueError("No paragliders has been found for race"
                                     " %s." % race_data[0][1])
        result = self._create_race(race_data[0], pgs)
        defer.returnValue(result)

    def _create_race(self, race_data, paragliders_row):
        # TODO: repository knows too much about Race's internals. Think about it
        i, rid, t, st, et, mst, met, tz, rt, chs = race_data
        participants = create_participants(paragliders_row)

        result = self.factory.create_race(t, rt, (mst, met), tz, rid)
        result._start_time = st
        result._end_time = et
        result._checkpoints = checkpoint_collection_from_geojson(chs)
        result._id = long(i)
        result.paragliders = participants['paragliders']
        return result

    @defer.inlineCallbacks
    def save(self, obj):
        result = []
        values = self._get_values_from_obj(obj)
        def insert_id(_id, _list):
            _list.insert(0, _id)
            return _list

        def save_new(cur):
            d = cur.execute(pe.insert('race'), values['race'])
            d.addCallback(lambda cur:cur.fetchone())
            d.addCallback(lambda x:
                ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s)",
                     (insert_id(x[0], p))) for p in values['paragliders']))
            d.addCallback(lambda pq:
                cur.execute("INSERT INTO paraglider VALUES " + pq +
                            "RETURNING ID;"))
            d.addCallback(lambda cur: cur.fetchone())
            return d

        def update(cur, pgs):
            d = cur.execute(pe.update('race'), values['race'])

            inobj = values['paragliders']
            indb = pgs
            for idx, p in enumerate(inobj):
                p.insert(0, obj._id)
                inobj[idx] = tuple(p)
            to_insert = set(inobj).difference(set(indb))
            to_delete = set(indb).difference(set(inobj))
            if to_delete:
                ids = tuple([x[1] for x in to_delete])
                d.addCallback(lambda _:
                cur.execute("DELETE FROM paraglider WHERE id=%s "
                            "AND person_id in %s", (obj._id, ids)))
            if to_insert:
                q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s)",
                                         (pitem)) for pitem in to_insert)
                d.addCallback(lambda _:
                        cur.execute("INSERT into paraglider values " + q))
                d.addCallback(lambda _: obj)
                return d


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
        result['race'] = (obj.title, obj.start_time, obj.end_time,
                          obj.timelimits[0], obj.timelimits[1],
                          obj.timezone, obj.type,
                          geojson_feature_collection(obj.checkpoints),
                          str(obj.id))
        result['paragliders'] = []
        for key in obj.paragliders:
            p = obj.paragliders[key]
            result['paragliders'].append([str(p.person_id), str(p.contest_number),
                                     p.country, p.glider, p.tracker_id,
                                     p._name.name, p._name.surname])
        return result

