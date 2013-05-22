'''
Test PostgreSQL implementation of IPersonRepository.
'''

__author__ = 'Boris Tsema'
from datetime import datetime
import time

from twisted.trial import unittest
from twisted.internet import defer
import mock

from gorynych.info.domain.test.helpers import create_contest, \
    create_checkpoints, create_race
from gorynych.info.infrastructure.persistence import PGSQLPersonRepository, PGSQLContestRepository, PGSQLRaceRepository, create_participants
# TODO: create separate module with test utils
from gorynych.info.domain.test.test_person import create_person
from gorynych.common.domain.types import geojson_feature_collection, checkpoint_collection_from_geojson, Name
from gorynych.info.domain.ids import PersonID, ContestID, RaceID
from gorynych.info.infrastructure.test import db_helpers
from gorynych.common.exceptions import NoAggregate, DatabaseValueError
from gorynych.common.infrastructure import persistence as pe


POOL = db_helpers.POOL


class PersonRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.repo = PGSQLPersonRepository(POOL)
        d = POOL.start()
        d.addCallback(lambda _:db_helpers.initDB('person', POOL))
        return d

    def tearDown(self):
        d = db_helpers.tearDownDB('person', POOL)
        d.addCallback(lambda _:POOL.close())
        return d

    @defer.inlineCallbacks
    def test_save_new(self):
        pers = create_person()
        saved_pers = yield self.repo.save(pers)
        self.assertEqual(pers, saved_pers,
                         'Something strange happend while saving.')
        self.assertIsNotNone(saved_pers._id)
        db_row = yield POOL.runQuery(pe.select('person'), (str(pers.id),))
        self.assertEqual(len(db_row), 1)
        db_row = db_row[0]
        self.assertTupleEqual(('John', 'Doe', 'UA', str(pers.id)),
                              (db_row[0], db_row[1], db_row[2], db_row[5]))

    @defer.inlineCallbacks
    def test_get_by_id(self):
        p_id = PersonID()
        date = datetime.now()
        p__id = yield POOL.runQuery(pe.insert('person'),
                        ('name', 'surname', date, 'ru', 'a@a.ru', str(p_id) ))
        saved_pers = yield self.repo.get_by_id(p_id)
        self.assertIsNotNone(saved_pers)
        self.assertTupleEqual(('Name Surname', 'RU', str(p_id)),
            (saved_pers.name.full(), saved_pers.country, str(saved_pers.id)))
        self.assertEqual(p__id[0][0], saved_pers._id)

    @defer.inlineCallbacks
    def test_get_by_nonexistent_id(self):
        p_id = "No such id"
        yield self.assertFailure(self.repo.get_by_id(p_id), NoAggregate)

    @defer.inlineCallbacks
    def test_update_existing(self):
        p_id = PersonID()
        date = datetime.now()
        yield POOL.runOperation(pe.insert('person'),
                        ('name', 'Surname', date, 'ru', 'a@a.ru', str(p_id) ))
        try:
            saved_pers = yield self.repo.get_by_id(p_id)
        except Exception:
            raise unittest.SkipTest(
                "Can't test because get_by_id isn't working.")
        if not saved_pers:
            raise unittest.SkipTest("Got nothing instead of Person.")
        
        saved_pers.country = 'USA'
        saved_pers.name = {'name': 'asfa'}
        s = yield self.repo.save(saved_pers)
        db_row = yield POOL.runQuery(pe.select('person'), (str(p_id),))
        self.assertTupleEqual(('Asfa', 'US'), (db_row[0][0], db_row[0][2]))
        

class ContestRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.repo = PGSQLContestRepository(POOL)
        d = POOL.start()
        d.addCallback(lambda _:db_helpers.initDB('contest', POOL))
        return d

    def tearDown(self):
       d = db_helpers.tearDownDB('contest', POOL)
       d.addCallback(lambda _:POOL.close())
       return d

    @defer.inlineCallbacks
    def test_get_by_id(self):
        c_id = ContestID()
        tz = 'Europe/Amsterdam'
        stime = int(time.time())
        etime = stime + 1
        c__id = yield POOL.runQuery(pe.insert('contest'),
            ('PGContest', stime, etime, tz, 'place', 'cou', 42.1, 42.2,
             str(c_id)))
        c__id = c__id[0][0]
        # Add participants to contest
        pg1_id = PersonID()
        pg2_id = PersonID()
        org1_id = PersonID()
        yield POOL.runOperation(pe.insert('participant', 'contest'),
            (str(c_id), str(pg1_id), 'paraglider', 'gl1', '15', '', 'person'))
        yield POOL.runOperation(pe.insert('participant', 'contest'),
            (str(c_id), str(pg2_id), 'paraglider', 'gl2', '18', '', 'person'))
        yield POOL.runOperation(pe.insert('participant', 'contest'),
            (str(c_id), str(org1_id), 'organizator', '', '', 'retrieve',
             'person'))
        # Add race_ids
        r_id = RaceID()
        r_id1 = RaceID()
        yield POOL.runOperation(pe.insert('race', 'contest'), (str(c_id),
                                                               str(r_id)))
        yield POOL.runOperation(pe.insert('race', 'contest'), (str(c_id),
                                                               str(r_id1)))

        # DB prepared, start test.
        cont = yield self.repo.get_by_id(c_id)
        self.assertEqual(cont.title, 'Pgcontest')
        self.assertEqual(cont.country, 'CO')
        self.assertEqual(cont.timezone, tz)
        self.assertEqual(cont.place, 'Place')
        self.assertEqual(cont._id, c__id)
        self.assertTupleEqual(cont.hq_coords, (42.1, 42.2))
        self.assertEquals((cont.start_time, cont.end_time), (stime, etime))
        self.assertIsInstance(cont.id, ContestID)
        self.assertDictEqual(cont._participants,
            {pg1_id : {'role': 'paraglider', 'contest_number':'15',
                       'glider':'gl1'},
             pg2_id: {'role':'paraglider', 'contest_number': '18',
                      'glider': 'gl2'},
             org1_id: {'role': 'organizator'}})
        self.assertListEqual(cont.race_ids, [str(r_id), str(r_id1)])


    @defer.inlineCallbacks
    def test_get_by_nonexistent_id(self):
        yield self.assertFailure(self.repo.get_by_id('Notexist'), NoAggregate)

    @defer.inlineCallbacks
    def test_get_list(self):
        self.repo.pool = mock.Mock()
        try:
            a = yield self.repo.get_list(offset=1)
        except:
            pass
        self.repo.pool.runQuery.assert_called_once_with(
            'select contest_id from contest limit 20 offset 1')

    def _prepare_participants(self, p_rows):
        participants = dict()
        for row in p_rows:
            pidsfs = PersonID.fromstring(row[1])
            participants[pidsfs] = dict(role=row[2])
            if row[4]:
                participants[pidsfs]['contest_number'] = int(row[4])
            if row[3]:
                participants[pidsfs]['glider'] = row[3]
        return participants

    @defer.inlineCallbacks
    def test_save_new(self):
        cont  = self._prepare_contest()

        saved_cont = yield self.repo.save(cont)
        self.assertEqual(cont, saved_cont)
        self.assertIsNotNone(saved_cont._id)
        raceids = yield POOL.runQuery(pe.select('race', 'contest'),
                                      (saved_cont._id,))
        raceids = [RaceID.fromstring(raceids[0][0]),
                   RaceID.fromstring(raceids[1][0])]
        self.assertListEqual(raceids, cont.race_ids)

        p_rows = yield POOL.runQuery(
            pe.select('participants', 'contest'), (saved_cont._id,))
        participants = self._prepare_participants(p_rows)
        self.assertDictEqual(participants, cont._participants)
        yield self._compare_contest_with_db(cont)

    def _prepare_contest(self):
        cid = ContestID()
        cont = create_contest(1, 5, id=cid)
        cont._participants = dict()
        pid1 = PersonID()
        cont._participants[pid1] = dict(role='paraglider',
                                        contest_number=13,
                                        glider='gl')
        pid2 = PersonID()
        cont._participants[pid2] = dict(role='paraglider',
                                        contest_number=14,
                                        glider='gl')
        pid3 = PersonID()
        cont._participants[pid3] = dict(role='organizator')
        rid1 = RaceID()
        rid2 = RaceID()
        cont.race_ids = [rid1, rid2]
        return cont


    @defer.inlineCallbacks
    def _compare_contest_with_db(self, cont):
        cont_row = yield POOL.runQuery(pe.select('contest'), (str(cont.id),))
        _i, _cid, _t, _st, _et, _tz, _pl, _co, _lat, _lon = cont_row[0]
        self.assertEqual(cont.title, _t)
        self.assertEqual(cont.country, _co)
        self.assertEqual(cont.timezone, _tz)
        self.assertEqual(cont.place, _pl)
        self.assertTupleEqual(cont.hq_coords, (_lat, _lon))
        self.assertEquals((cont.start_time, cont.end_time), (_st, _et))
        self.assertEqual(str(cont.id), _cid)

    @defer.inlineCallbacks
    def test_save_existent(self):
        cont = self._prepare_contest()
        s_cont1 = yield self.repo.save(cont)

        s_cont1.title = "New Title"
        rid3 = RaceID()
        s_cont1.race_ids.append(rid3)
        pers1 = s_cont1._participants.popitem()

        s_cont2 = yield self.repo.save(s_cont1)


        self.assertEqual(s_cont1._id, s_cont2._id)
        raceids = yield POOL.runQuery(pe.select('race', 'contest'),
                                      (s_cont1._id,))

        p_rows = yield POOL.runQuery(
            pe.select('participants', 'contest'), (s_cont1._id,))
        participants = self._prepare_participants(p_rows)
        self.assertDictEqual(participants, cont._participants)

        raceids = [RaceID.fromstring(raceids[0][0]),
                   RaceID.fromstring(raceids[1][0]),
                   RaceID.fromstring(raceids[2][0])]
        for raid in raceids:
            self.assertTrue(raid in s_cont1.race_ids, "Race update failed.")

        yield self._compare_contest_with_db(s_cont1)


class RaceRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.repo = PGSQLRaceRepository(POOL)
        d = POOL.start()
        d.addCallback(lambda _:db_helpers.initDB('race', POOL))
        d.addCallback(lambda _: POOL.runOperation(
            pe.insert('racetype', 'race'), ('racetogoal',)))
        return d

    def tearDown(self):
        d = db_helpers.tearDownDB('contest', POOL)
        d.addCallback(lambda _:POOL.close())
        return d

    @defer.inlineCallbacks
    def _prepare_race(self):
        rid = RaceID()
        t = 'Racetitle'
        tz = 'Europe/Amsterdam'
        chs = create_checkpoints()
        st = 1347711300
        et = 1347732000
        _chs = geojson_feature_collection(chs)
        r_id = yield POOL.runQuery(pe.insert('race'),
                (t, st, et, st-1, et+1, tz,
                 'racetogoal', (geojson_feature_collection(chs)), str(rid)))

        defer.returnValue(
            (r_id[0][0], rid, t, st, et, st-1, et+1, tz, 'racetogoal', chs))

    def _compare_race(self, i, ri, t, st, et, mst, met, tz, rt, chs, rc):
        self.assertEqual(rc._id, i)
        self.assertEqual(rc.id, ri)
        self.assertEqual(rc.title, t)
        self.assertEqual(rc.start_time, st)
        self.assertEqual(rc.end_time, et)
        self.assertEqual(rc.timelimits, (mst, met))
        self.assertEqual(rc.timezone, tz)
        self.assertEqual(rc.type, rt)
        self.assertEqual(rc.checkpoints, chs)

    @defer.inlineCallbacks
    def test_by_id(self):
        i, ri, t, st, et, mst, met, tz, rt, chs = yield self._prepare_race()
        yield self.assertFailure(self.repo.get_by_id(ri), DatabaseValueError)
        pid = PersonID()
        yield POOL.runOperation(pe.insert('paraglider', 'race'),
            (i, str(pid), '1', 'ru', 'gl1', '', 'alex', 't'))

        rc = yield self.repo.get_by_id(ri)

        self._compare_race(i, ri, t, st, et, mst, met, tz, rt, chs, rc)

    @defer.inlineCallbacks
    def test_get_by_nonexistent_id(self):
        yield self.assertFailure(self.repo.get_by_id("not exist"), NoAggregate)

    @defer.inlineCallbacks
    def test_save(self):
        self.maxDiff = None
        rc = create_race()
        saved_rc = yield self.repo.save(rc)
        self._compare_race(saved_rc._id, rc.id, rc.title, rc.start_time,
                           rc.end_time, rc.timelimits[0], rc.timelimits[1],
                           rc.timezone, rc.type,
                rc.checkpoints, saved_rc)

        race_row = yield POOL.runQuery(pe.select('race'), (str(rc.id),))
        i, ri, t, st, et, mst, met, tz, rt, chs = race_row[0]
        self._compare_race(i, ri, t, st, et, mst, met, tz, rt,
                           checkpoint_collection_from_geojson(chs), rc)

        pg_row = yield POOL.runQuery(pe.select('paragliders', 'race'),
                                     (saved_rc._id,))
        pgs = create_participants(pg_row)['paragliders']
        for key in pgs:
            self.assertEqual(pgs[key], rc.paragliders[key])

    @defer.inlineCallbacks
    def test_update(self):
        rc = create_race()
        saved_rc = yield self.repo.save(rc)
        saved_rc.title = 'Updated title'
        saved_rc._start_time = rc._start_time - 300
        saved_rc._checkpoints.pop()
        chs = saved_rc.checkpoints
        chkey = saved_rc.paragliders.keys()[0]
        saved_rc.paragliders[chkey]._name = Name("Mitrofan", "Ignatov")
        updated_rc = yield self.repo.save(rc)
        self._compare_race(saved_rc._id, saved_rc.id, saved_rc.title,
                           saved_rc._start_time, saved_rc.end_time, saved_rc.timelimits[0], saved_rc.timelimits[1], saved_rc.timezone,
                           saved_rc.type, chs, updated_rc)

        race_row = yield POOL.runQuery(pe.select('race'), (str(rc.id),))
        i, ri, t, st, et, mst, met, tz, rt, chs = race_row[0]
        self._compare_race(i, ri, t, st, et, mst, met, tz, rt,
                           checkpoint_collection_from_geojson(chs), rc)
        pg_row = yield POOL.runQuery(pe.select('paragliders', 'race'),
                                     (saved_rc._id,))
        pgs = create_participants(pg_row)['paragliders']
        for key in pgs:
            self.assertEqual(pgs[key], rc.paragliders[key])
