# coding=utf-8
import gc
from copy import deepcopy

import mock

from shapely.geometry import Point
from pytz.exceptions import UnknownTimeZoneError

from twisted.trial import unittest
from twisted.internet import defer

from gorynych.info.domain.test.helpers import create_checkpoints
from gorynych.info.application import ApplicationService
from gorynych.common.domain.types import Checkpoint
from gorynych.common.infrastructure.messaging import FakeRabbitMQService
from gorynych.info.application import LastPointApplication


class GoodRepository():
    store = dict()
    def is_store_empty(self):
        return len(self.store) == 0
    def clean_store(self):
        self.store = dict()
    def save(self, obj):
        self.store[obj.id] = obj
        return obj
    def get_by_id(self, id):
        result = deepcopy(self.store.get(id))
        return result
    def get_list(self, limit=None, offset=0):
        results = self.store.values()
        if offset >= len(results):
            return None
        else:
            results = results[offset:]
        if limit:
            return results[:limit]
        else:
            return results

    def persist(self, event):
        pass


class BadContestRepository:
    def save(self, obj):
        raise IndentationError("boom")


class ApplicationServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.cs = ApplicationService(mock.Mock(), mock.Mock())
        self.cs.startService()
        self.repository = GoodRepository()
        if not self.repository.is_store_empty():
            self.repository.clean_store()

    def tearDown(self):
        self.repository.clean_store()
        del self.repository
        self.cs.stopService()
        del self.cs
        gc.collect()


@mock.patch('gorynych.common.infrastructure.persistence.get_repository')
class ContestServiceTest(ApplicationServiceTestCase):

    def test_succes_contest_creation(self, patched):
        patched.return_value = self.repository
        cont1 = self.cs.create_new_contest(
            dict(title='hoi', start_time=1,
                 end_time=2, place='Боливия',
                 country='RU',
                 hq_coords=[12.3, 42.9],
                 timezone='Europe/Moscow')).result
        self.assertEqual(cont1.title, 'hoi', "Bad return")
        self.assertEqual(cont1.id.id[:5], 'cnts-', "Bad return")

        saved_result = self.repository.get_by_id(cont1.id)
        self.assertEqual(saved_result.title, 'hoi',
                         "Bad contest storing.")
        self.assertEqual(saved_result.timezone, 'Europe/Moscow',
                         "Bad contest storing.")

        cont2 = self.cs.get_contest({'contest_id': cont1.id}).result
        self.assertEqual(cont1.hq_coords, cont2.hq_coords)
        self.assertEqual(cont1.title, cont2.title)

        cont_list = self.cs.get_contests().result
        self.assertEqual(cont2.id, cont_list[0].id)

        new_cont = self.cs.change_contest(dict(contest_id=cont1.id,
            title='A', start_time=2, end_time='6',
            timezone='Canada/Eastern')).result
        saved_result = self.repository.get_by_id(cont1.id)
        self.assertEqual(saved_result.timezone, 'Canada/Eastern',
                         "Timezone hasn't been changed.")
        self.assertEqual(new_cont.id, cont1.id, "ID has been chanding during"
                                                " contest edit.")
        self.assertEqual(self.repository.get_by_id(cont1.id).title, 'A')


    def test_bad_contest_saving(self, patched):
        patched.return_value = BadContestRepository()
        d = self.cs.create_new_contest(dict(title='hoi', start_time=3,
            end_time=5, place='Боливия', country='RU',
            hq_coords=[12.3, 42.9], timezone='Europe/Moscow'))
        self.assertFailure(d, IndentationError)


    def test_wront_times_in_contest_creation(self, patched):
        patched.return_value = self.repository
        d = defer.Deferred()
        d.addCallback(self.cs.create_new_contest)
        d.callback(dict(title='hoi', start_time=3, end_time=2,
            place='Боливия', country='RU',
            hq_coords=[12.3, 42.9], timezone='1'))
        self.assertFailure(d, ValueError, "Time invariants wasn't checked.")

    def test_wront_timezone_in_contest_creation(self, patched):
        patched.return_value = self.repository
        d = defer.Deferred()
        d.addCallback(self.cs.create_new_contest)
        d.callback(dict(title='hoi', start_time=1, end_time=2,
                        place='Боливия', country='RU',
                        hq_coords=[12.3, 42.9], timezone='1'))
        self.assertFailure(d, UnknownTimeZoneError,
                           "Time invariants wasn't checked.")


    def test_read_contest(self, patched):
        patched.return_value = self.repository
        result = self.cs.get_contest({'contest_id':'cc'}).result
        self.assertIsNone(result)

    def test_read_contests(self, patched):
        patched.return_value = self.repository
        result = self.cs.get_contests({'limit':100, 'offset':'2'}).result
        self.assertIsNone(result)


@mock.patch('gorynych.common.infrastructure.persistence.get_repository')
class PersonServiceTest(ApplicationServiceTestCase):

    def test_create_person(self, patched):
        patched.return_value = self.repository

        pers1 = self.cs.create_new_person(dict(name='Vasya', surname='Doe',
            country='QQ', email='john@example.com', reg_date='2012,12,21')
                                ).result
        self.assertEqual(pers1.name.full(), 'Vasya Doe')
        self.assertEqual(pers1, self.repository.get_by_id(pers1.id))

        pers2 = self.cs.get_person({'person_id': pers1.id}).result
        self.assertEqual(pers1, pers2)

        another_person = self.cs.create_new_person(dict(name='Vasya',
                                                        surname='Do',
            country='QQ', email='joh@example.com', reg_date='2012,12,21')
                                ).result

        self.assertNotEqual(pers1.id, another_person.id,
                            "Person with the same id has been created.")

        pers_list = self.cs.get_persons().result
        self.assertIsInstance(pers_list, list)
        id_list = [pers.id for pers in pers_list]
        self.assertTrue(pers1.id in id_list)

        new_pers = self.cs.change_person(dict(person_id=pers1.id,
            name='Evlampyi')).result
        self.assertEqual(new_pers.name.full(), 'Evlampyi Doe')
        self.assertEqual(self.repository.get_by_id(new_pers.id)
        ._name.name, 'Evlampyi')

    def test_read_person(self, patched):
        patched.return_value = self.repository
        result = self.cs.get_person({'person_id':'1'}).result
        self.assertIsNone(result)


    def test_read_persons(self, patched):
        patched.return_value = self.repository
        result = self.cs.get_persons().result
        self.assertIsNone(result)

        result = self.cs.get_persons({'limit':100, 'offset':'20'}).result
        self.assertIsNone(result)


@mock.patch('gorynych.common.infrastructure.persistence.get_repository')
class ContestParagliderRaceTest(unittest.TestCase):
    def setUp(self):
        self.skipTest('Need rework.')
        from gorynych.info.domain.tracker import TrackerID
        self.aps = ApplicationService(mock.Mock(), mock.Mock())
        self.aps.startService()
        self.repository = GoodRepository()
        if not self.repository.is_store_empty():
            self.repository.clean_store()

        @mock.patch('gorynych.common.infrastructure.persistence.get_repository')
        def fixture(patched):
            patched.return_value = self.repository
            c = self.aps.create_new_contest(dict(title='hoi', start_time=1,
                end_time=2, place='Боливия', country='RU',
                hq_coords=[12.3, 42.9], timezone='Europe/Moscow')).result
            p1 = self.aps.create_new_person(dict(name='Vasya', surname='Doe',
                country='QQ', email='vas@example.com',
                reg_date='2012,12,21')).result
            p2 = self.aps.create_new_person(dict(name='John', surname='Doe',
                country='QQ', email='john@example.com',
                reg_date='2012,12,21')).result
            return c.id, p1.id, p2.id

        try:
            self.cont_id, self.p1_id, self.p2_id = fixture()
        except:
            raise unittest.SkipTest("Fixture can't be created.")
        if not self.cont_id and self.p1_id and self.p2_id:
            raise unittest.SkipTest("I need ids for work.")
        pers = self.repository.get_by_id(self.p1_id)
        self.tracker_id = TrackerID('tr203', '12')
        pers.assign_tracker(self.tracker_id)
        self.repository.save(pers)

    def tearDown(self):
        self.repository.clean_store()
        del self.repository
        self.aps.stopService()
        del self.aps
        gc.collect()

    def test_register_paraglider_on_contest(self, patched):
        patched.return_value = self.repository
        result = self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p1_id)).result
        paraglider = result.paragliders[self.p1_id]
        cont = self.repository.get_by_id(self.cont_id)
        self.assertEqual(len(cont.paragliders), 1)
        self.assertEqual(cont._participants[self.p1_id]['role'], 'paraglider')

        self.assertEqual(paraglider['glider'], 'gin')
        self.assertEqual(paraglider['contest_number'], 1)

        self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p1_id))
        self.assertEqual(len(cont.paragliders), 1, "The same paraglider was "
                                                   "registered twice.")

        d = self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p2_id))
        self.assertFailure(d, ValueError, "Contest numbers are not uniq!")

        self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='2',
            person_id=self.p2_id))
        cont = self.repository.get_by_id(self.cont_id)
        self.assertEqual(len(cont.paragliders), 2, "Can't register another "
                                                   "paraglider.")

        paragliders_list = self.aps.get_contest_paragliders(dict
            (contest_id=self.cont_id)).result
        self.assertDictContainsSubset({'glider': 'gin', 'contest_number': 1},
             paragliders_list[self.p1_id])

    def test_change_paraglider(self, patched):
        patched.return_value = self.repository
        try:
            self.aps.register_paraglider_on_contest(dict(
                contest_id=self.cont_id, glider='gin', contest_number='1',
                person_id=self.p1_id))
        except Exception:
            raise unittest.SkipTest("Paraglider need to be registered for "
                                    "this test.")
        result = self.aps.change_paraglider(dict(contest_id=self.cont_id,
            person_id=self.p1_id, glider='very cool glider',
            contest_number='1986')).result

        # Check is everything correct in persistence store.
        cont = self.repository.get_by_id(self.cont_id)
        paraglider = cont.paragliders[self.p1_id]
        self.assertEqual(paraglider['glider'], 'very',
            "Paraglider wasn't changed correctly.")
        self.assertEqual(paraglider['contest_number'], 1986,
            "Paraglider wasn't changed correctly.")

        # Check correct return.
        self.assertEqual(result.paragliders[self.p1_id]['glider'], 'very',
            "Paraglider wasn't returned correctly.")
        self.assertEqual(result.paragliders[self.p1_id]['contest_number'],
                         1986,
            "Paraglider wasn't returned correctly.")

    def test_create_new_race_for_contest(self, patched):
        patched.return_value = self.repository
        try:
            self.aps.register_paraglider_on_contest(dict(
                contest_id=self.cont_id, glider='gin', contest_number='1',
                person_id=self.p1_id))
        except:
            raise unittest.SkipTest("Paraglider need to be registered.")

        chs = create_checkpoints()

        race = self.aps.create_new_race_for_contest(
                                            dict(contest_id=self.cont_id,
                                                 race_type='speedrun',
                                                 title='task 3',
                                                 checkpoints=chs)).result
        saved_race = self.repository.get_by_id(race.id)
        self.assertEqual(race.id, saved_race.id)
        self.assertEqual(race.type, 'speedrun')
        self.assertEqual(saved_race.type, 'speedrun')
        self.assertEqual(race.title, 'Task 3')
        self.assertEqual(saved_race.title, 'Task 3')
        saved_contest = self.repository.get_by_id(self.cont_id)
        # self.assertEqual(saved_contest.race_ids[0], race.id,
        #                  "Race hasn't been saved.")

    def test_get_contest_races(self, patched):
        patched.return_value = self.repository
        try:
            self.aps.register_paraglider_on_contest(dict(
                contest_id=self.cont_id, glider='gin', contest_number='1',
                person_id=self.p1_id))
            self.aps.register_paraglider_on_contest(dict(
                contest_id=self.cont_id, glider='mantra', contest_number='4',
                person_id=self.p2_id))
            ch1 = Checkpoint('A', Point(0.1, 2), radius=400, times=(1, 2))
            self.aps.create_new_race_for_contest(dict(contest_id=self.cont_id,
                                                      race_type='speedrun',
                                                      title='task 3',
                                                      checkpoints=[ch1]))
            self.aps.create_new_race_for_contest(dict(contest_id=self.cont_id,
                                                      race_type='speedrun',
                                                      title='task 4',
                                                      checkpoints=[ch1]))
        except Exception:
            raise unittest.SkipTest("Race is needed for this test.")
        races = self.aps.get_contest_races(dict(contest_id=self.cont_id))\
            .result
        self.assertIsInstance(races, list)
        self.assertEqual(len(races), 2)
        self.assertEqual(races[0].type, 'speedrun')
        saved_contest = self.repository.get_by_id(self.cont_id)
        self.assertEqual(len(saved_contest.race_ids), 2)

        race1 = self.repository.get_by_id(races[0].id)
        race2 = self.repository.get_by_id(races[1].id)


class TestLastPointApplicationRabbitMQService(unittest.TestCase):
    def setUp(self):
        self.sender = FakeRabbitMQService(LastPointApplication)

    def test_message_transfer(self):
        message = "Hi! I'm a message!"
        self.sender.write(message)
        received = self.sender.read(message)
        self.assertEquals(received, message)
