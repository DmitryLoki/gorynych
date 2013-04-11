# coding=utf-8
import gc

import mock

from shapely.geometry import Point

from zope.interface import implements
from twisted.trial import unittest
from twisted.internet import defer

from gorynych.info.application import ApplicationService, read_person
from gorynych.common.domain.types import Checkpoint


class GoodRepository:
    store = dict()
    def is_store_empty(self):
        return len(self.store) == 0
    def clean_store(self):
        self.store = dict()
    def save(self, obj):
        self.store[obj.id] = obj
        return obj
    def get_by_id(self, id):
        return self.store.get(id)
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


class BadContestRepository:
    def save(self, obj):
        raise IndentationError("boom")


class ApplicationServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.cs = ApplicationService(mock.Mock())
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
        d = self.cs.create_new_contest(dict(title='hoi', start_time=1,
            end_time=2, place='Боливия', country='RU',
            hq_coords=[12.3, 42.9]))
        cont1 = d.result
        self.assertEqual(cont1['contest_title'], 'Hoi')
        self.assertEqual(len(cont1['contest_id']), 36)

        cont2 = self.cs.get_contest({'contest_id': cont1['contest_id']}
                ).result
        self.assertDictEqual(cont1, cont2)

        cont_list = self.cs.get_contests().result
        self.assertEqual(cont2['contest_id'], cont_list[0]['contest_id'])

        new_cont = self.cs.change_contest(dict(contest_id=cont1['contest_id'],
            title='A', start_time=2, end_time='6')).result
        self.assertEqual(new_cont['contest_title'], 'A')
        self.assertEqual(self.repository.get_by_id(cont1['contest_id']
                ).title, 'A')


    def test_bad_contest_saving(self, patched):
        patched.return_value = BadContestRepository()
        d = self.cs.create_new_contest(dict(title='hoi', start_time=3,
            end_time=5, place='Боливия', country='RU',
            hq_coords=[12.3, 42.9]))
        self.assertFailure(d, IndentationError)


    def test_bad_contest_creation(self, patched):
        patched.return_value = self.repository
        d = defer.Deferred()
        d.addCallback(self.cs.create_new_contest)
        d.callback(dict(title='hoi', start_time=3, end_time=2,
            place='Боливия', country='RU',
            hq_coords=[12.3, 42.9]))
        self.assertFailure(d, ValueError)


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
        self.assertEqual(pers1['person_name'], 'Vasya Doe')
        self.assertDictEqual(pers1,
                        read_person(self.repository.get_by_id
                            (pers1['person_id'])))

        pers2 = self.cs.get_person({'person_id':pers1['person_id']}).result
        self.assertDictEqual(pers1, pers2)

        pers_list = self.cs.get_persons().result
        self.assertIsInstance(pers_list, list)
        self.assertEqual(pers1['person_id'], pers_list[0]['person_id'])

        new_pers = self.cs.change_person(dict(person_id=pers1['person_id'],
            name='Evlampyi')).result
        self.assertEqual(new_pers['person_name'], 'Evlampyi Doe')
        self.assertEqual(self.repository.get_by_id(new_pers['person_id'])
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


class ContestParagliderRaceTest(unittest.TestCase):
    def setUp(self):
        from gorynych.info.domain.tracker import TrackerID
        self.aps = ApplicationService(mock.Mock())
        self.aps.startService()
        self.repository = GoodRepository()
        if not self.repository.is_store_empty():
            self.repository.clean_store()

        @mock.patch('gorynych.common.infrastructure.persistence.get_repository')
        def fixture(patched):
            patched.return_value = self.repository
            c = self.aps.create_new_contest(dict(title='hoi', start_time=1,
                end_time=2, place='Боливия', country='RU',
                hq_coords=[12.3, 42.9])).result
            p1 = self.aps.create_new_person(dict(name='Vasya', surname='Doe',
                country='QQ', email='vas@example.com',
                reg_date='2012,12,21')).result
            p2 = self.aps.create_new_person(dict(name='John', surname='Doe',
                country='QQ', email='john@example.com',
                reg_date='2012,12,21')).result
            return c['contest_id'], p1['person_id'], p2['person_id']

        self.cont_id, self.p1_id, self.p2_id = fixture()
        pers = self.repository.get_by_id(self.p1_id)
        pers.assign_tracker(TrackerID(15))
        self.repository.save(pers)

    def tearDown(self):
        del self.repository
        self.aps.stopService()
        del self.aps
        gc.collect()


    @mock.patch('gorynych.common.infrastructure.persistence.get_repository')
    def test_register_paraglider(self, patched):
        patched.return_value = self.repository
        result = self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p1_id)).result
        cont = self.repository.get_by_id(self.cont_id)
        self.assertEqual(len(cont.paragliders), 1)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['glider'], 'gin')
        self.assertEqual(result['contest_number'], 1)
        self.assertTrue(result.has_key('person_id'))

        self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p1_id))
        self.assertEqual(len(cont.paragliders), 1)

        d = self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p2_id))
        self.assertFailure(d, ValueError, "Contest numbers are not uniq!")

        self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='2',
            person_id=self.p2_id))
        self.assertEqual(len(cont.paragliders), 2, "Can't register another "
                                                   "paraglider.")

        paragliders_list = self.aps.get_contest_paragliders(dict
            (contest_id=self.cont_id)).result
        self.assertTrue({'person_id': self.p1_id, 'glider': 'gin',
                         'contest_number': '1'} in paragliders_list)


    @mock.patch('gorynych.common.infrastructure.persistence.get_repository')
    def test_create_new_race(self, patched):
        patched.return_value = self.repository
        self.aps.register_paraglider_on_contest(dict(
            contest_id=self.cont_id, glider='gin', contest_number='1',
            person_id=self.p1_id))
        ch1 = Checkpoint('A', Point(0.1, 2), radius=400)

        race = self.aps.create_new_race_for_contest(dict(contest_id=self
                .cont_id, race_type='speedrun', race_title='task 3',
            checkpoints=[ch1])).result
        self.assertEqual(race['race_id'], self.repository.get_by_id
            (race['race_id'])
        .id)
        self.assertEqual(race['race_type'], 'speedrun')




if __name__ == '__main__':
    unittest.main()
