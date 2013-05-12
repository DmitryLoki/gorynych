from twisted.internet import defer
from zope.interface.declarations import implements

from gorynych.info.domain.contest import ContestFactory, IContestRepository
from gorynych.common.exceptions import NoAggregate
from gorynych.common.infrastructure import persistence as pe
from gorynych.info.domain.ids import PersonID


class PGSQLContestRepository(object):
    implements(IContestRepository)

    def __init__(self, pool):
        self.pool = pool

    @defer.inlineCallbacks
    def get_by_id(self, contest_id):
        rows = yield self.pool.runQuery(pe.select('contest'),
                                        (str(contest_id),))
        if not rows:
            raise NoAggregate("Contest")
        cont = self._create_contest_from_data(rows[0])
        cont = yield self._append_data_to_contest(cont)
        defer.returnValue(cont)

    @defer.inlineCallbacks
    def _append_data_to_contest(self, cont):
        participants = yield self.pool.runQuery(
                    pe.select('participants', 'contest'), (cont._id,))
        if participants:
            cont = self._add_participants_to_contest(cont, participants)
        races = yield self.pool.runQuery(pe.select('race', 'contest'),
                                         (cont._id,))
        if races:
            for race_id in races:
                cont.race_ids.append(race_id[0])
        defer.returnValue(cont)

    def _create_contest_from_data(self, row):
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
        return cont

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
    def get_list(self, limit=20, offset=None):
        result = []
        command = "select id from contest"
        if limit:
            command += ' limit ' + str(limit)
        if offset:
            command += ' offset ' + str(offset)
        ids = yield self.pool.runQuery(command)
        for idx, cid in enumerate(ids):
            cont = yield self.get_by_id(cid[0])
            result.append(cont)
        defer.returnValue(result)

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

            d = cur.execute(pe.insert('contest'), values['contest'])
            d.addCallback(lambda cur: cur.fetchone())


            if values['participants']:
                # Callbacks wan't work in for loop, so i insert multiple values
                # in one query.
                # Oh yes, executemanu also wan't work in asynchronous mode.
                d.addCallback(lambda x:
                    ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)",
                       (insert_id(x[0], p))) for p in values['participants']))
                d.addCallback(lambda q:
                  cur.execute("INSERT into participant values " + q +
                              "RETURNING id;"))
                d.addCallback(lambda cur: cur.fetchone())

            if values['race_ids']:
                d.addCallback(lambda x:
                    ','.join(cur.mogrify("(%s, %s)",
                             (x[0], str(p))) for p in values['race_ids']))
                d.addCallback(lambda q:
                    cur.execute("INSERT into contest_race values " + q + ""
                                                 "RETURNING ID;"))
            d.addCallback(lambda cur: cur.fetchone())
            return d

        def update(cur, prts, rids):
            d = cur.execute(pe.update('contest'), values['contest'])
            # print values
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
                    d.addCallback(lambda _:
                        cur.execute("DELETE FROM participant WHERE id=%s "
                            "AND participant_id in %s", (obj._id, ids)))
                if to_insert:
                    q = ','.join(cur.mogrify("(%s, %s, %s, %s, %s, %s, %s)",
                                    (pitem)) for pitem in to_insert)
                    d.addCallback(lambda _:
                        cur.execute("INSERT into participant values " + q))

            if values['race_ids'] or rids:
                inobj = values['race_ids']
                indb = rids
                for idx, r in enumerate(inobj):
                    inobj[idx] = (obj._id, str(r))
                to_insert = set(inobj).difference(set(indb))
                to_delete = set(indb).difference(set(inobj))
                if to_delete:
                    rids = tuple([x[0] for x in to_delete])
                    d.addCallback(lambda _:
                     cur.execute("DELETE FROM contest_race WHERE id=%s AND "
                                 "race_id in %s", (obj._id, rids)))
                if to_insert:
                    rq = ','.join(cur.mogrify("(%s, %s)",
                                             (ritem)) for ritem in to_insert)
                    d.addCallback(lambda _:
                    cur.execute("INSERT into contest_race values " + rq))

            d.addCallback(lambda _:obj)
            return d

        result = None
        if obj._id:
            prts = yield self.pool.runQuery(pe.select('participants',
                                                      'contest'), (obj._id,))
            rids = yield self.pool.runQuery(pe.select('race', 'contest'),
                                            (obj._id,))
            result = yield self.pool.runInteraction(update, prts, rids)
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

        result['race_ids'] = obj.race_ids[::]
        return result
