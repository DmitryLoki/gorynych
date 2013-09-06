import unittest

import mock
import time
from copy import deepcopy

from gorynych.common.domain import events
from gorynych.info.domain.test.helpers import create_contest
from gorynych.info.domain import contest, person, race
from gorynych.common.domain.types import Address, Name, Country
from gorynych.info.domain.ids import PersonID, RaceID, TrackerID, TransportID


class MockedPersonRepository(mock.Mock):
    '''
    Necessary only for tracker assignment.
    '''
    def get_by_id(self, key):
        person = mock.Mock()
        person.name = Name('name', 'surname')
        person.country = Country('RU')
        if key == 'person1':
            person.tracker = 'tracker1'
        elif key == 'person2':
            person.tracker = 'tracker2'
        elif key == 'person3':
            person.tracker = None
        return person


class ContestFactoryTest(unittest.TestCase):

    def test_contestid_successfull_contest_creation(self):
        cont = create_contest(1, 2)
        self.assertIsInstance(cont.address, Address)
        self.assertEqual(cont.title, 'Hello world')
        self.assertEqual(cont.country, 'RU')
        self.assertEqual(cont.timezone, 'Europe/Moscow')
        self.assertEqual(cont.place, 'Yrupinsk')
        self.assertEquals((cont.start_time, cont.end_time), (1, 2))
        self.assertIsInstance(cont.id, contest.ContestID)
        self.assertIsNone(cont._id)

        cont2 = create_contest(3, 4)
        self.assertNotEqual(cont.id, cont2.id,
                            "Contest with the same id has been created.")

    def test_str_successfull_contest_creation(self):
        cont = create_contest(1, 3, id='cnts-130422-12345')
        self.assertEqual(cont.end_time, 3)
        self.assertEqual(cont.start_time, 1)
        self.assertEqual(cont.id, 'cnts-130422-12345')

    def test_unsuccessfull_contest_creation(self):
        self.assertRaises(ValueError, create_contest, 3, 1,
                          "Contest can be created with wrong times.")


class EventsApplyingTest(unittest.TestCase):
    def test_ContestRaceCreated(self):
        cont = create_contest(1, 2)
        rid = RaceID()
        ev = events.ContestRaceCreated(cont.id, rid)
        self.assertRaises(AssertionError, cont.apply, ev)
        cont.apply([ev])
        self.assertEqual(len(cont.race_ids), 1)
        cont.apply([ev])
        self.assertEqual(len(cont.race_ids), 1)
        rid = RaceID()
        ev = events.ContestRaceCreated(cont.id, rid)
        cont.apply([ev])
        self.assertEqual(len(cont.race_ids), 2)


class ContestTest(unittest.TestCase):
    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_register_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store
        cont = create_contest(1, 2)
        p1 = person.PersonID()
        c = cont.register_paraglider(p1, 'mantrA 9', '747')

        self.assertIsInstance(c, contest.Contest)
        self.assertEqual(len(cont._participants), 1)
        self.assertEqual(len(cont.paragliders), 1)
        self.assertIsInstance(cont.paragliders, dict, "It must be dict.")
        self.assertEqual(cont._participants[p1]['role'], 'paraglider')
        self.assertEqual(cont._participants[p1]['glider'], 'mantra')
        self.assertEqual(cont._participants[p1]['contest_number'], 747)

        p2 = person.PersonID()
        cont.register_paraglider(p2, 'mantrA 9', '757')
        self.assertEqual(len(cont._participants), 2)
        self.assertEqual(cont._participants[p2]['role'], 'paraglider')
        self.assertEqual(cont._participants[p2]['glider'], 'mantra')
        self.assertEqual(cont._participants[p2]['contest_number'], 757)

        # Check contest numbers uniqueness.
        self.assertRaises(ValueError, cont.register_paraglider, 'person3',
            'mantrA 9', '757')

        mock_calls = event_store.mock_calls
        self.assertEqual(len(mock_calls), 2)
        self.assertEqual(mock_calls[-1], mock.call.persist(
            events.ParagliderRegisteredOnContest(p2, cont.id)))
        self.assertEqual(mock_calls[-2], mock.call.persist(
            events.ParagliderRegisteredOnContest(p1, cont.id)))


    def test_times_changing(self):
        cont = create_contest(1, '15')
        cont.start_time = '2'
        self.assertEqual(cont.start_time, 2)
        cont.end_time = '8'
        self.assertEqual(cont.end_time, 8)
        self.assertRaises(ValueError, setattr, cont, 'start_time', 8)
        self.assertRaises(ValueError, setattr, cont, 'start_time', 9)
        self.assertRaises(ValueError, setattr, cont, 'end_time', 2)
        self.assertRaises(ValueError, setattr, cont, 'end_time', 1)
        cont.change_times('10', '16')
        self.assertEqual((cont.start_time, cont.end_time), (10, 16))
        self.assertRaises(ValueError, cont.change_times, '10', '8')

    def test_change_title(self):
        cont = create_contest(1, '15')
        cont.title = '  hello moOn  '
        self.assertEqual(cont.title, 'hello moOn')

    def test_change_address(self):
        cont = create_contest(1, '15')
        cont.place = 'Severodvinsk'
        self.assertEqual(cont.place, 'Severodvinsk')
        cont.country = 'tw'
        self.assertEqual(cont.country, 'TW')
        cont.hq_coords = (15, 0)
        self.assertEqual(cont.hq_coords, (15, 0))


class ContestTestWithRegisteredParagliders(unittest.TestCase):

    def setUp(self):
        self.p1_id = person.PersonID()
        self.p2_id = person.PersonID()
        self.p3_id = person.PersonID()
        @mock.patch('gorynych.common.infrastructure.persistence.event_store')
        def fixture(patched):
            patched.return_value = mock.Mock()
            cont  = create_contest(1, 15)
            cont.register_paraglider(self.p2_id, 'mantrA 9', '757')
            cont.register_paraglider(self.p1_id, 'gIn 9', '747')
            person1 = cont._participants[self.p1_id]
            person2 = cont._participants[self.p2_id]
            return cont, person1, person2
        try:
            self.cont, self.person1, self.person2 = fixture()
        except:
            raise unittest.SkipTest("ERROR: need contest with paragliders "
                                    "for test.")


    def tearDown(self):
        del self.cont
        del self.person1
        del self.person2

    def test_correct_change_participant_data(self):
        self.cont.change_participant_data(self.p1_id, glider='ajAx  ',
            contest_number='0')
        self.assertEqual(self.person1['glider'], 'ajax')
        self.assertEqual(self.person1['contest_number'], 0)

    def test_no_data(self):
        self.assertRaises(ValueError, self.cont.change_participant_data,
            'person2')

    def test_wrong_parameters(self):
        self.assertRaises(ValueError, self.cont.change_participant_data,
            'person3', contest_number=9, glider='ajax')
        self.cont.change_participant_data(self.p1_id, cotest_number=9,
            glider='aJax')
        self.assertEqual(self.person1['contest_number'], 747)
        self.assertEqual(self.person1['glider'], 'ajax')

    def test_violate_invariants(self):
        self.assertRaises(ValueError, self.cont.change_participant_data,
            'person1', contest_number='757')


class ParagliderTest(unittest.TestCase):
    def test_success_creation(self):
        p_id = PersonID()
        t_id = TrackerID(TrackerID.device_types[0], '123456789012345')
        p = race.Paraglider(p_id, Name('Vasya', 'Pupkin'),
                            Country('RU'), 'Mantra 9', 15, t_id)
        self.assertEqual(p.person_id, p_id)
        self.assertEqual(p.glider, 'mantra')
        self.assertEqual(p.contest_number, 15)
        self.assertEqual(p.tracker_id, t_id)


@mock.patch('gorynych.common.infrastructure.persistence.event_store')
class ContestServiceTest(unittest.TestCase):

    def setUp(self):
        self.cont = create_contest(time.time(), time.time() + 3600)
    
    def test_register_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        alone_cont = deepcopy(self.cont)
        pid = PersonID()
        populated_cont = self.cont.register_paraglider(pid,
                                                       'glider',
                                                       11)
        self.assertFalse(alone_cont.paragliders)
        self.assertTrue(populated_cont.paragliders)

        pgl = populated_cont.paragliders
        self.assertEquals(pgl.keys()[0], pid)
        self.assertEquals(pgl[pid]['role'], 'paraglider')
        self.assertEquals(pgl[pid]['glider'], 'glider')
        self.assertEquals(pgl[pid]['contest_number'], 11)

    def test_add_transport(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        alone_cont = deepcopy(self.cont)
        tid = TransportID()
        populated_cont = self.cont.add_transport(tid)

        self.assertFalse(alone_cont.transport)
        self.assertIn(tid, populated_cont.transport)

    def test_change_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        pid = PersonID()
        cont = self.cont.register_paraglider(pid,
                                             'glider',
                                             11)
        changed_cont = contest.change_participant(cont, dict(glider='noglider',
                                                             contest_number=21,
                                                             person_id=pid))

        pgl = changed_cont.paragliders

        self.assertEquals(pgl.keys()[0], pid)
        self.assertEquals(pgl[pid]['glider'], 'noglider')
        self.assertEquals(pgl[pid]['contest_number'], 21)
