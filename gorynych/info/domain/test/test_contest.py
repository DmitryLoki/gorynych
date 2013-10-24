import unittest

import mock
import time
from copy import deepcopy

from gorynych.common.domain import events
from gorynych.info.domain.test.helpers import create_contest, create_person, create_transport
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
        p = create_person()
        p_id = str(p.id)
        c = cont.register_paraglider(p, 'mantrA 9', '747')

        self.assertIsInstance(c, contest.Contest)
        self.assertEqual(len(cont.paragliders), 1)
        self.assertEqual(len(cont.paragliders), 1)
        self.assertIsInstance(cont.paragliders, dict, "It must be dict.")
        self.assertEqual(cont.paragliders[p_id]['role'], 'paraglider')
        self.assertEqual(cont.paragliders[p_id]['glider'], 'mantra')
        self.assertEqual(cont.paragliders[p_id]['contest_number'], 747)

        p2 = create_person()
        p2_id = str(p2.id)
        cont.register_paraglider(p2, 'mantrA 9', '757')
        self.assertEqual(len(cont.paragliders), 2)
        self.assertEqual(cont.paragliders[p2_id]['role'], 'paraglider')
        self.assertEqual(cont.paragliders[p2_id]['glider'], 'mantra')
        self.assertEqual(cont.paragliders[p2_id]['contest_number'], 757)

        # Check contest numbers uniqueness.
        p3 = create_person()
        self.assertRaises(ValueError, cont.register_paraglider, p3,
            'mantrA 9', '757')

        mock_calls = event_store.mock_calls
        self.assertEqual(len(mock_calls), 2)
        self.assertEqual(mock_calls[-1], mock.call.persist(
            events.ParagliderRegisteredOnContest(p2.id, cont.id)))
        self.assertEqual(mock_calls[-2], mock.call.persist(
            events.ParagliderRegisteredOnContest(p.id, cont.id)))


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
        self.p1 = create_person()
        self.p2 = create_person()
        self.p3 = create_person()

        @mock.patch('gorynych.common.infrastructure.persistence.event_store')
        def fixture(patched):
            patched.return_value = mock.Mock()
            cont = create_contest(1, 15)
            cont.register_paraglider(self.p2, 'mantrA 9', '757')
            cont.register_paraglider(self.p1, 'gIn 9', '747')
            person1 = cont.paragliders[self.p1.id]
            person2 = cont.paragliders[self.p2.id]
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
        self.cont.change_participant_data(self.p1.id, glider='ajAx  ',
            contest_number='0')
        self.assertEqual(self.person1['glider'], 'ajax')
        self.assertEqual(self.person1['contest_number'], 0)

    def test_no_data(self):
        self.assertRaises(ValueError, self.cont.change_participant_data,
            'person2')

    def test_wrong_parameters(self):
        self.assertRaises(ValueError, self.cont.change_participant_data,
            'person3', contest_number=9, glider='ajax')
        self.cont.change_participant_data(self.p1.id, cotest_number=9,
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
        p = create_person()
        populated_cont = self.cont.register_paraglider(p,
                                                       'glider',
                                                       11)
        self.assertFalse(alone_cont.paragliders)
        self.assertTrue(populated_cont.paragliders)

        pgl = populated_cont.paragliders
        self.assertEquals(pgl.keys()[0], p.id)
        self.assertEquals(pgl[p.id]['role'], 'paraglider')
        self.assertEquals(pgl[p.id]['glider'], 'glider')
        self.assertEquals(pgl[p.id]['contest_number'], 11)

    def test_add_winddummy(self, patched):
        alone_cont = deepcopy(self.cont)
        p = create_person()
        populated_cont = self.cont.add_winddummy(p)

        self.assertFalse(alone_cont.winddummies)
        self.assertIn(p.id, populated_cont.winddummies)

    def test_add_organizer(self, patched):
        alone_cont = deepcopy(self.cont)
        p = create_person()
        populated_cont = self.cont.add_organizer(p, description='some guy')

        self.assertFalse(alone_cont.organizers)
        self.assertIn(p.id, populated_cont.organizers)
        self.assertEquals(populated_cont.organizers[p.id]['description'], 'some guy')

    def test_add_transport_staffmember(self, patched):
        alone_cont = deepcopy(self.cont)
        t = contest.StaffMember(title='t', type='bus')
        populated_cont = self.cont.add_staff_member(t)

        self.assertFalse(alone_cont.staff)
        self.assertIn(t.id, populated_cont.staff)
        self.assertEquals(populated_cont.staff[t.id]['type'], 'bus')

    def test_add_rescuer_staffmember(self, patched):
        alone_cont = deepcopy(self.cont)
        r = contest.StaffMember(title='r', type='rescuer')
        populated_cont = self.cont.add_staff_member(r)

        self.assertFalse(alone_cont.staff)
        self.assertIn(r.id, populated_cont.staff)
        self.assertEquals(populated_cont.staff[r.id]['type'], 'rescuer')

    def test_change_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        p = create_person()
        cont = self.cont.register_paraglider(p,
                                             'glider',
                                             11)
        changed_cont = contest.change_participant(cont, dict(glider='noglider',
                                                             contest_number=21,
                                                             person_id=p.id))

        pgl = changed_cont.paragliders

        self.assertEquals(pgl.keys()[0], p.id)
        self.assertEquals(pgl[p.id]['glider'], 'noglider')
        self.assertEquals(pgl[p.id]['contest_number'], 21)


class StaffMemberTest(unittest.TestCase):
    def test_type(self):
        self.assertRaises(TypeError, contest.StaffMember,
                          title='Scruffy the janitor', type='janitor',
                          description="Don't know who that guy is")
        sm = contest.StaffMember(title="Chip'n'Dale", type='rescuer',
                                 description='rescue ranger!')
        self.assertIsInstance(sm, contest.StaffMember)
        self.assertEquals(sm.title, "Chip'n'Dale")
        self.assertEquals(sm.type, "rescuer")
        self.assertEquals(sm.description, "rescue ranger!")
        self.assertFalse(sm.phone)

    def test_phone(self):
        self.assertRaises(ValueError, contest.StaffMember,
                          title='Serenity', type='ambulance',
                          description='firefly-class starship', phone='nope')
        sm = contest.StaffMember(title='Millenium Falcon', type='ambulance',
                                 description='piece of junk', phone='+3456324433')
        self.assertIsInstance(sm, contest.StaffMember)
        self.assertEquals(sm.title, "Millenium Falcon")
        self.assertEquals(sm.type, "ambulance")
        self.assertEquals(sm.description, "piece of junk")
        self.assertEquals(sm.phone, '+3456324433')
