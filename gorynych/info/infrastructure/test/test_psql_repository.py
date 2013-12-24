'''
Test PostgreSQL implementation of IPersonRepository.
'''

__author__ = 'Boris Tsema'
from datetime import datetime
import time
from random import randint
import psycopg2

from twisted.trial import unittest
from twisted.internet import defer
import mock

from gorynych.info.domain.test.helpers import create_checkpoints, create_race, create_tracker, create_transport
from gorynych.info.infrastructure import persistence
from gorynych.info.domain.test import helpers
from gorynych.info.domain.test.test_contest import create_role
from gorynych.common.domain.types import geojson_feature_collection, checkpoint_collection_from_geojson, Name, Phone
from gorynych.info.domain.ids import PersonID, ContestID, RaceID, TrackerID
from gorynych.info.infrastructure.test import db_helpers
from gorynych.common.infrastructure import persistence as pe
from gorynych.common.exceptions import NoAggregate, DatabaseValueError
from gorynych.info.domain import contest


POOL = db_helpers.POOL


class MockeryTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.repo = self.repo_type(POOL)
            self.patch = mock.patch(
                'gorynych.info.infrastructure.persistence.pe'
                '.event_store')
            self.pe = self.patch.start()
            m = mock.Mock()
            m.load_events.return_value = []
            m.load_events_for_aggregates.return_value = {}
            self.pe.return_value = m
            d = db_helpers.initDB(self.sql_file, POOL)
            return d
        except:
            pass

    def tearDown(self):
        try:
            del self.repo
            self.patch.stop()
            return db_helpers.tearDownDB(self.sql_file, POOL)
        except:
            pass

    @defer.inlineCallbacks
    def get_by_nonexistent_id(self):
        p_id = "No such id"
        yield self.assertFailure(self.repo.get_by_id(p_id), NoAggregate)


class TransportRepositoryTest(MockeryTestCase):
    repo_type = persistence.PGSQLTransportRepository
    sql_file = 'transport'

    test_transport_type = 'motorcycle'

    def setUp(self):
        d = super(TransportRepositoryTest, self).setUp()
        d.addCallback(lambda _: POOL.runOperation(
            'insert into transport_type(transport_type) values(%s)',
            (self.test_transport_type,)))
        return d

    @defer.inlineCallbacks
    def test_save_new(self):
        transport = create_transport(self.test_transport_type)
        saved = yield self.repo.save(transport)
        self.assertEqual(saved, transport)
        db_row = yield POOL.runQuery(pe.select('transport'),
            (str(transport.id),))
        self.assertEqual(len(db_row), 1)
        db_row = db_row[0]

        self.assertTupleEqual(
            (transport.type, transport.title, transport.description),
            (db_row[3], db_row[2], db_row[4]))

    @defer.inlineCallbacks
    def test_get_by_id(self):
        transport = create_transport(self.test_transport_type)
        yield self.repo.save(transport)
        saved = yield self.repo.get_by_id(transport.id)
        self.assertEqual(saved.type, transport.type)
        self.assertEqual(saved.title, transport.title)
        self.assertEqual(saved.description, transport.description)

    def test_get_by_nonexistent_id(self):
        return super(TransportRepositoryTest, self).get_by_nonexistent_id()

    @defer.inlineCallbacks
    def test_update(self):
        transport = create_transport(self.test_transport_type)
        yield self.repo.save(transport)
        transport.title = 'Some other name'
        yield self.repo.save(transport)

        trs = yield self.repo.get_list()
        self.assertTrue(len(trs) == 1)
        updated = trs[0]

        self.assertEqual(transport.type, updated.type)
        self.assertEqual(transport.title, updated.title)
        self.assertEqual(transport.description, updated.description)


class TrackerRepositoryTest(MockeryTestCase):
    repo_type = persistence.PGSQLTrackerRepository
    sql_file = 'tracker'

    def setUp(self):
        d = super(TrackerRepositoryTest, self).setUp()
        d.addCallback(lambda _: POOL.runOperation(
            'insert into device_type(name) values(%s)', ('tr203',)))
        return d

    @defer.inlineCallbacks
    def test_save_new(self):
        tracker = create_tracker()
        saved = yield self.repo.save(tracker)
        self.assertEqual(saved, tracker)
        db_row = yield POOL.runQuery(pe.select('tracker'), (str(tracker.id),))
        self.assertEqual(len(db_row), 1)
        db_row = db_row[0]
        self.assertTupleEqual((tracker.device_id, tracker.device_type,
        TrackerID(
            tracker.device_type, tracker.device_id),
        tracker.name),
            (db_row[0], db_row[1], db_row[2], db_row[3]))

    @defer.inlineCallbacks
    def test_get_by_id(self):
        tracker = create_tracker()
        yield self.repo.save(tracker)
        saved = yield self.repo.get_by_id(tracker.id)
        self.assertEqual(saved.id, tracker.id)
        self.assertEqual(saved.device_id, tracker.device_id)
        self.assertEqual(saved.device_type, tracker.device_type)
        self.assertEqual(saved.name, tracker.name)

    def test_get_by_nonexistent_id(self):
        return super(TrackerRepositoryTest, self).get_by_nonexistent_id()

    @defer.inlineCallbacks
    def test_assign(self):
        tracker = create_tracker()
        saved = yield self.repo.save(tracker)
        yield POOL.runOperation(
            'insert into tracker_assignees(id, assignee_id, assigned_for) values(%s, %s, %s)',
            (saved._id, 'some_guy', 'for the sake of good'))
        ass = yield self.repo._get_assignee(saved._id)
        self.assertEqual(ass, {'for the sake of good': 'some_guy'})

        # unique contraint has to be broken
        self.assertFailure(
            POOL.runOperation(
                'insert into tracker_assignees(id, assignee_id, assigned_for) values(%s, %s, %s)',
                (saved._id, 'some_guy', 'for the sake of good')),
            psycopg2.IntegrityError)

    @defer.inlineCallbacks
    def test_update(self):
        tracker = create_tracker()
        yield self.repo.save(tracker)
        tracker.name = 'some other name'
        yield self.repo.save(tracker)

        tracks = yield self.repo.get_list()
        self.assertTrue(len(tracks) == 1)
        updated = tracks[0]

        self.assertEqual(updated.id, tracker.id)
        self.assertEqual(updated.device_id, tracker.device_id)
        self.assertEqual(updated.device_type, tracker.device_type)
        self.assertEqual(updated.name, tracker.name)


class PersonRepositoryTest(MockeryTestCase):
    repo_type = persistence.PGSQLPersonRepository
    sql_file = 'person'

    @defer.inlineCallbacks
    def test_save_new(self):
        email = 'a@a.ru_' + str(randint(1, 10000))
        pers = helpers.create_person(email=email)
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
            ('name', 'surname', date, 'ru', 'a@a.ru', str(p_id)))
        saved_pers = yield self.repo.get_by_id(p_id)
        self.assertIsNotNone(saved_pers)
        self.assertTupleEqual(('Name Surname', 'RU', str(p_id)),
            (saved_pers.name.full(), saved_pers.country, str(saved_pers.id)))
        self.assertEqual(p__id[0][0], saved_pers._id)

    def test_get_by_nonexistent_id(self):
        return super(PersonRepositoryTest, self).get_by_nonexistent_id()

    @defer.inlineCallbacks
    def test_update_existing(self):
        p_id = PersonID()
        date = datetime.now()
        yield POOL.runOperation(pe.insert('person'),
            ('name', 'Surname', date, 'ru', 'a@a.ru', str(p_id)))
        try:
            saved_pers = yield self.repo.get_by_id(p_id)
        except Exception:
            raise unittest.SkipTest(
                "Can't test because get_by_id isn't working.")
        if not saved_pers:
            raise unittest.SkipTest("Got nothing instead of Person.")

        saved_pers.country = 'USA'
        saved_pers.name = {'name': 'asfa'}
        yield self.repo.save(saved_pers)
        db_row = yield POOL.runQuery(pe.select('person'), (str(p_id),))
        self.assertTupleEqual(('Asfa', 'US'), (db_row[0][0], db_row[0][2]))

    @defer.inlineCallbacks
    def test_save_duplicate(self):
        email = 'a@a.ru'
        pers = helpers.create_person(email=email)
        pers2 = helpers.create_person(email=email)
        saved_pers = yield self.repo.save(pers)
        saved_pers2 = yield self.repo.save(pers)
        self.assertNotEqual(pers.id, pers2.id)
        self.assertEqual(saved_pers.id, saved_pers2.id)


class ContestRepositoryTest(MockeryTestCase):
    repo_type = persistence.PGSQLContestRepository
    sql_file = 'contest'

    @defer.inlineCallbacks
    def test_get_by_id(self):
        c_id = ContestID()
        tz = 'Europe/Amsterdam'
        stime = int(time.time())
        etime = stime + 1
        c__id = yield POOL.runQuery(pe.insert('contest'),
            ('PGContest', stime, etime, tz, 'place', 'cou', 42.1, 42.2,
            'android', str(c_id)))
        c__id = c__id[0][0]
        # Add participants to contest
        pg1_id = PersonID()
        pg2_id = PersonID()
        org1_id = PersonID()
        p1row = (c__id, str(pg1_id), 'paraglider', 'gl1', '15', '', '', '+71',
            'John Doe', '', 'RU', '')
        p2row = (c__id, str(pg2_id), 'paraglider', 'gl2', '18', '', '', '',
            'Vasya Ivanov', '', 'CA', '')
        o1row = (c__id, str(org1_id), 'organizer', '', '', 'retrieve', '',
            '+88', 'Daniel Petrenko', 'dan@email.org', '', '')
        yield POOL.runOperation(pe.insert('participant', 'contest'), p1row)
        yield POOL.runOperation(pe.insert('participant', 'contest'), p2row)
        yield POOL.runOperation(pe.insert('participant', 'contest'), o1row)

        # DB prepared, start test.
        cont = yield self.repo.get_by_id(c_id)
        self.assertIsInstance(cont, contest.Contest)
        self.assertIsInstance(cont.id, ContestID)
        self.assertEqual(cont.title, 'PGContest')
        self.assertEqual(cont.address.country.code(), 'CO')
        self.assertEqual(cont.timezone, tz)
        self.assertEqual(cont.address.place, 'Place')
        self.assertEqual(cont._id, c__id)
        self.assertTupleEqual(cont.address.coordinates, (42.1, 42.2))
        self.assertEquals((cont.start_time, cont.end_time), (stime, etime))
        self.assertEqual(cont.retrieve_id, 'android')
        # Check participants.
        self.assertEqual(cont.paragliders[pg1_id], contest.Paraglider(
            pg1_id, 15, 'gl1', 'RU', Name('John', 'Doe'), Phone('+71')))
        self.assertEqual(cont.paragliders[pg2_id], contest.Paraglider(
            pg2_id, 18, 'gl2', 'CA', Name('Vasya', 'Ivanov')))
        self.assertEqual(cont.organizers[org1_id], contest.Organizer(
            org1_id, 'dan@email.org', Name('Daniel', 'Petrenko'), 'retrieve'))

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
        cont = self._prepare_contest()

        saved_cont = yield self.repo.save(cont)
        self.assertEqual(cont, saved_cont)
        self.assertIsNotNone(saved_cont._id)
        p_rows = yield POOL.runQuery(
            pe.select('participants', 'contest'), (saved_cont._id,))
        participants = self._prepare_participants(p_rows)
        self.assertDictEqual(participants, cont._participants)
        yield self._compare_contest_with_db(cont)

    def _prepare_contest(self):
        cid = ContestID()
        cont = helpers.create_contest(1, 5, id=cid)
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

        p_rows = yield POOL.runQuery(
            pe.select('participants', 'contest'), (s_cont1._id,))
        participants = self._prepare_participants(p_rows)
        self.assertDictEqual(participants, cont._participants)

        yield self._compare_contest_with_db(s_cont1)

    def test_get_by_nonexistent_id(self):
        return super(ContestRepositoryTest, self).get_by_nonexistent_id()


class RaceRepositoryTest(MockeryTestCase):
    repo_type = persistence.PGSQLRaceRepository
    sql_file = 'race'

    def setUp(self):
        d = super(RaceRepositoryTest, self).setUp()

        d.addCallback(lambda _: POOL.runOperation(
            'insert into race_type(type) values(%s)', ('racetogoal',)))
        d.addCallback(lambda _: db_helpers.initDB('transport', POOL))
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
            (t, st, et, tz,
            'racetogoal', _chs, None, st - 1, et + 1, str(rid)))

        defer.returnValue(
            (
                r_id[0][0], rid, t, st, et, st - 1, et + 1, tz, 'racetogoal',
                chs))

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
        # raw_input()
        i, ri, t, st, et, mst, met, tz, rt, chs = yield self._prepare_race()
        yield self.assertFailure(self.repo.get_by_id(ri), DatabaseValueError)
        pid = PersonID()
        yield POOL.runOperation(pe.insert('paraglider', 'race'),
            (i, str(pid), '1', 'ru', 'gl1', '', 'alex', 't'))

        rc = yield self.repo.get_by_id(ri)

        self._compare_race(i, ri, t, st, et, mst, met, tz, rt, chs, rc)

    def test_get_by_nonexistent_id(self):
        return super(RaceRepositoryTest, self).get_by_nonexistent_id()

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
        # print len(race_row[0])
        i, ri, t, st, et, tz, rt, chs, smth, mst, met = race_row[0]
        self._compare_race(i, ri, t, st, et, mst, met, tz, rt,
            checkpoint_collection_from_geojson(chs), rc)

        pg_row = yield POOL.runQuery(pe.select('paragliders', 'race'),
            (saved_rc._id,))
        pgs = {p.contest_number: p
            for p in persistence.create_participants(pg_row)}
        for key in pgs:
            # can't use __eq__ here because after _get_values_from_obj None tracker_id becomes ''
            # and I'm not sure if I'm allowed to change it
            self.assertEqual(pgs[key].person_id, rc.paragliders[key].person_id)
            self.assertEqual(pgs[key].glider, rc.paragliders[key].glider)
            self.assertEqual(pgs[
                key].contest_number, rc.paragliders[key].contest_number)
            self.assertTrue(not pgs[
                key].tracker_id and not rc.paragliders[key].tracker_id)

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
            saved_rc.start_time, saved_rc.end_time, saved_rc.timelimits[
                0], saved_rc.timelimits[1], saved_rc.timezone,
            saved_rc.type, chs, updated_rc)

        race_row = yield POOL.runQuery(pe.select('race'), (str(rc.id),))
        i, ri, t, st, et, tz, rt, chs, smth, mst, met = race_row[0]
        self._compare_race(i, ri, t, st, et, mst, met, tz, rt,
            checkpoint_collection_from_geojson(chs), rc)
        pg_row = yield POOL.runQuery(pe.select('paragliders', 'race'),
            (saved_rc._id,))
        pgs = {p.contest_number: p
            for p in persistence.create_participants(pg_row)}
        for key in pgs:
            # same shit as in test_save
            self.assertEqual(pgs[key].person_id, rc.paragliders[key].person_id)
            self.assertEqual(pgs[key].glider, rc.paragliders[key].glider)
            self.assertEqual(pgs[
                key].contest_number, rc.paragliders[key].contest_number)
            self.assertTrue(not pgs[
                key].tracker_id and not rc.paragliders[key].tracker_id)
        yield db_helpers.tearDownDB('transport', POOL)
