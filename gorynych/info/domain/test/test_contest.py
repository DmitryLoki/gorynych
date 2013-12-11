import unittest
import time

import mock

from gorynych.common.domain import events, model
from gorynych.info.domain.test.helpers import create_contest, create_person, create_checkpoints
from gorynych.info.domain import contest
from gorynych.common.domain.types import Address, Name, Country, Phone, MappingCollection
from gorynych.info.domain.ids import PersonID, RaceID
from gorynych.common.exceptions import DomainError


class MockedPersonRepository(mock.Mock):
    '''
    Necessary only for tracker assignment.
    '''
    # TODO: check necessity and correctness of this class.
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


def create_role(rolename, pers=None, **kw):
    if pers is None:
        pers = create_person()
    try:
        if rolename.lower() == 'paraglider':
            result = contest.Paraglider(pers.id, kw['cnum'],
                kw.get('glider', 'mantra'), pers.country, pers.name,
                kw.get('phone'))
        elif rolename.lower() == 'organizer':
            result = contest.Organizer(pers.id, kw['email'], pers.name,
                kw.get('description', None))
        elif rolename.lower() == 'winddummy':
            result = contest.Winddummy(pers.id, kw['phone'], pers.name)
        else:
            raise ValueError(
                "Wrong argument passed during role creation: %s" % rolename)
    except Exception as e:
        raise unittest.SkipTest("ERROR: contest.%s can't be created: %r" %
                                (rolename.capitalize(), e))
    return pers, result


class ContestFactoryTest(unittest.TestCase):
    def test_contestid_successfull_contest_creation(self):
        cont = create_contest(1, 2)
        self.assertIsInstance(cont.address, Address)
        self.assertEqual(cont.title, 'Hello world')
        self.assertEqual(cont.address, Address('Yrupinsk', 'RU', '45.23,-23.22'))
        self.assertEqual(cont.timezone, 'Europe/Moscow')
        #self.assertEqual(cont.place, 'Yrupinsk')
        self.assertEquals((cont.start_time, cont.end_time), (1, 2))
        self.assertIsInstance(cont.id, contest.ContestID)
        self.assertIsNone(cont._id)
        self.assertEqual(len(cont.paragliders), 0)
        self.assertEqual(len(cont.organizers), 0)
        self.assertEqual(len(cont.staff), 0)
        self.assertEqual(len(cont.winddummies), 0)
        self.assertIsNone(cont.retrieve_id)

        cont2 = create_contest(3, 4)
        self.assertNotEqual(cont.id, cont2.id,
            "Contest with the same id has been created.")

    def test_str_successfull_contest_creation(self):
        cont = create_contest(1, 3, id='cnts-130422-12345')
        self.assertEqual(cont.end_time, 3)
        self.assertEqual(cont.start_time, 1)
        self.assertEqual(cont.id, 'cnts-130422-12345')
        self.assertIsInstance(cont.id, contest.ContestID)

    def test_creation_with_wrong_times(self):
        self.assertRaises(ValueError, create_contest, 3, 1,
            "Contest can be created with wrong times.")


class EventsApplyingTest(unittest.TestCase):
    def test_ContestRaceCreated(self):
        cont = create_contest(1, 2)
        rid = RaceID()
        ev = events.ContestRaceCreated(cont.id, rid)
        self.assertRaises(AssertionError, cont.apply, ev)
        cont.apply([ev])
        self.assertFalse(hasattr(cont, 'race_ids'), "New version don't has "
                                                    "race_id set.")


class ContestTest(unittest.TestCase):
    @unittest.expectedFailure
    def test_times_changing(self):
        cont = create_contest(1, '15')
        cont.start_time = '2'
        self.assertEqual(cont.start_time, 2)
        cont.end_time = '8'
        self.assertEqual(cont.end_time, 8)
        self.assertRaises(ValueError, setattr, cont, 'start_time', 8)
        self.assertRaises(ValueError, setattr, cont, 'start_time', 9)
        self.assertRaises(DomainError, setattr, cont, 'end_time', 2)
        self.assertRaises(DomainError, setattr, cont, 'end_time', 1)
        cont.change_times('10', '16')
        self.assertEqual((cont.start_time, cont.end_time), (10, 16))
        self.assertRaises(ValueError, cont.change_times, '10', '8')

    def test_change_title(self):
        cont = create_contest(1, '15')
        cont.title = '  hello moOn  '
        self.assertEqual(cont.title, 'hello moOn')

    def test_change_address(self):
        cont = create_contest(1, '15')
        cont.address = Address('Severodvinsk', 'tw', (15, 0))
        self.assertEqual(cont.address, Address('Severodvinsk', 'tw', (15, 0)))


class TestInvariants(unittest.TestCase):
    def setUp(self):
        self.cont = create_contest(time.time(), time.time() + 3600)

    def tearDown(self):
        del self.cont

    def test_person_only_in_one_role_fail(self):
        p1 = mock.MagicMock(); p1.id = 1
        self.cont.paragliders[1] = p1
        self.cont.staff[0] = p1
        self.cont.organizers[1] = p1
        self.assertRaises(DomainError, contest.person_only_in_one_role,
            self.cont)

    def test_person_only_in_one_role_success(self):
        self.cont.paragliders[1] = 1
        self.cont.organizers[2] = 1
        self.assertIsNone(contest.person_only_in_one_role(self.cont))


class ContestTestWithRegisteredParagliders(unittest.TestCase):
    def setUp(self):
        self.p1 = create_person()
        self.p2 = create_person()
        self.p3 = create_person()

        @mock.patch('gorynych.common.infrastructure.persistence.event_store')
        def fixture(patched):
            patched.return_value = mock.Mock()
            cont = create_contest(1, 15)
            _, par2 = create_role('paraglider', pers=self.p2, glider='mantra',
                cnum='757')
            _, par1 = create_role('paraglider', pers=self.p1, glider='gin',
                cnum='747')
            _, org = create_role('organizer', self.p3,
                                email='john@example.org')
            cont.add_paraglider(par1)
            cont.add_paraglider(par2)
            cont.add_organizer(org)
            return cont, par1, par2
        try:
            self.cont, self.person1, self.person2 = fixture()
        except Exception as e:
            raise unittest.SkipTest("ERROR: need contest with paragliders "
                                    "for test. %r" % e)

    def tearDown(self):
        del self.cont
        del self.person1
        del self.person2

    def test_correct_change_participant_data(self):
        cont = contest.change_participant(self.cont, 'paraglider', self.p1.id,
                                      glider='ajAx', contest_number='0')
        self.assertIsInstance(cont, contest.Contest)
        self.assertEqual(self.cont.paragliders[self.p1.id].glider, 'ajax')
        self.assertEqual(self.cont.paragliders[self.p1.id].contest_number, 0)

    def test_absent_role(self):
        self.assertRaises(ValueError, contest.change_participant, self.cont,
            'paragliders', self.p1.id, glider='ajax')

    def test_absent_id(self):
        self.assertRaises(ValueError, contest.change_participant, self.cont,
            'paragliders', self.p3.id, glider='ajax')

    def test_no_data(self):
        cont = contest.change_participant(self.cont, 'paraglider', self.p1.id)
        self.assertEqual(self.cont.paragliders[self.p1.id].glider, 'gin')
        self.assertIsInstance(cont, contest.Contest)

    def test_violate_invariants(self):
        self.assertRaises(DomainError, contest.change_participant, self.cont,
            'paraglider', self.p1.id, glider='ajax', contest_number=757)

    def test_change_organizer(self):
        cont = contest.change_participant(self.cont, 'organizer',
            self.p3.id, email='vas@mail.ru', name=Name('Vasisualy', 'Lohankin'))
        self.assertIsInstance(cont, contest.Contest)
        self.assertIsInstance(cont.organizers[self.p3.id], contest.Organizer)


class TestAddingToContest(unittest.TestCase):

    def setUp(self):
        self.cont = create_contest(time.time(), time.time() + 3600)

    def tearDown(self):
        del self.cont

    def test_add_winddummy(self):
        p, w = create_role('winddummy', phone='+712')
        c = self.cont.add_winddummy(w)

        self.assertTrue(len(self.cont.winddummies) > 0)
        self.assertIsInstance(c, contest.Contest)
        self.assertIsInstance(c.winddummies, MappingCollection)
        self.assertIn(w.id, self.cont.winddummies.keys())
        self.assertEqual(w.id, self.cont.winddummies[w.id].id)

    def test_add_organizer(self):
        p, o = create_role('organizer', email='john@example.com')
        populated_cont = self.cont.add_organizer(o)
        self.assertIsInstance(populated_cont, contest.Contest)
        self.assertEqual(len(self.cont.organizers), 1)
        self.assertIn(p.id, populated_cont.organizers.keys())
        self.assertEqual(p.id, populated_cont.organizers[p.id].id)
        self.assertIsInstance(populated_cont.organizers[p.id],
            contest.Organizer)

        # Add another organizer.
        p2, o2 = create_role('organizer', email='john@example.com')
        populated_cont = self.cont.add_organizer(o2)
        self.assertIsInstance(populated_cont, contest.Contest)
        self.assertEqual(len(self.cont.organizers), 2)
        self.assertIn(p2.id, populated_cont.organizers.keys())
        self.assertEqual(p2.id, populated_cont.organizers[p2.id].id)
        self.assertIsInstance(populated_cont.organizers[p2.id],
            contest.Organizer)

    def test_add_staffmember(self):
        t = contest.Staff(title='t', type='bus')
        populated_cont = self.cont.add_staff(t)
        self.assertIsInstance(populated_cont, contest.Contest)
        self.assertEqual(len(self.cont.staff), 1)
        self.assertIn(t.id, populated_cont.staff.keys())
        self.assertEqual(t.id, populated_cont.staff[t.id].id)
        self.assertEqual(t, populated_cont.staff[t.id])

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_register_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        # Register first paraglider.
        p, par = create_role('paraglider', cnum=0, glider='mantra')
        c = self.cont.add_paraglider(par)
        self.assertIsInstance(c, contest.Contest)
        self.assertEqual(len(self.cont.paragliders), 1)
        self.assertIsInstance(self.cont.paragliders, MappingCollection)
        self.assertIsInstance(self.cont.paragliders[p.id], contest.Paraglider)
        self.assertEqual(self.cont.paragliders[p.id].id, p.id)

        # Register second paraglider.
        p2, par2 = create_role('paraglider', cnum='1', glider='mantra')
        c2 = self.cont.add_paraglider(par2)
        self.assertIsInstance(c2, contest.Contest)
        self.assertEqual(len(self.cont.paragliders), 2)
        self.assertIsInstance(self.cont.paragliders, MappingCollection)
        self.assertIsInstance(self.cont.paragliders[p2.id], contest.Paraglider)
        self.assertEqual(self.cont.paragliders[p2.id].id, p2.id)
        self.assertNotEqual(self.cont.paragliders[p.id],
            self.cont.paragliders[p2.id])

        # Check contest numbers uniqueness.
        p3, par3 = create_role('paraglider', cnum='1', glider='mantra')
        self.assertRaises(DomainError, self.cont.add_paraglider, par3)
        self.assertEqual(len(self.cont.paragliders), 2)
        self.assertIn(1,self.cont.paragliders.get_attribute_values(
            'contest_number'))
        self.assertIn(0,self.cont.paragliders.get_attribute_values(
            'contest_number'))

        mock_calls = event_store.mock_calls
        self.assertEqual(len(mock_calls), 2)
        self.assertEqual(mock_calls[-1], mock.call.persist(events.ParagliderRegisteredOnContest(p2.id, self.cont.id)))
        self.assertEqual(mock_calls[-2], mock.call.persist(events.ParagliderRegisteredOnContest(p.id, self.cont.id)))

    def test_add_same_pers_as_organizer_and_paraglider(self):
        p1, org = create_role('organizer', email='john@example.com')
        p2, par = create_role('paraglider', pers=p1, cnum=1)
        try:
            c = self.cont.add_organizer(org)
        except Exception as e:
            raise unittest.SkipTest("ERROR: organizer can't be added: %r" % e)
        self.assertRaises(DomainError, self.cont.add_paraglider, par)
        self.assertEqual(1, len(self.cont.organizers))
        self.assertEqual(0, len(self.cont.paragliders))


class StaffMemberTest(unittest.TestCase):
    def test_type(self):
        self.assertRaises(TypeError, contest.Staff, title='Scruffy the janitor',
            type='janitor',  description="Don't know who that guy is")
        sm = contest.Staff(title="Chip'n'Dale", type='rescuer',
            description='rescue ranger!')
        self.assertIsInstance(sm, contest.Staff)
        self.assertIsInstance(sm.id, model.DomainIdentifier)
        self.assertEquals(sm.title, "Chip'n'Dale")
        self.assertEquals(sm.type, "rescuer")
        self.assertEquals(sm.description, "rescue ranger!")
        self.assertFalse(sm.phone)

    def test_phone(self):
        self.assertRaises(ValueError, contest.Staff, title='Serenity',
            type='ambulance', description='firefly-class starship', phone='nope')
        self.assertRaises(TypeError, contest.Staff, title='Serenity',
            type='ambulance', description='firefly-class starship', phone=1)
        sm = contest.Staff(title='Millenium Falcon', type='ambulance',
            description='piece of junk', phone='+3456324433')
        self.assertIsInstance(sm, contest.Staff)
        self.assertIsInstance(sm.phone, Phone)
        self.assertEquals(sm.title, "Millenium Falcon")
        self.assertEquals(sm.type, "ambulance")
        self.assertEquals(sm.description, "piece of junk")
        self.assertEquals(sm.phone, Phone('+3456324433'))

    def test_equality(self):
        sm = contest.Staff(title="Chip'n'Dale", type='rescuer',
            description='rescue ranger!')
        sm2 = contest.Staff(title="Chip'n'Dale", type='rescuer',
            description='rescue ranger!', id=sm.id)
        self.assertEqual(sm, sm2)

    def test_nonequality(self):
        sm = contest.Staff(title="Chip'n'Dale", type='rescuer',
            description='rescue ranger!')
        sm2 = contest.Staff(title="Chip'n'Dale", type='ambulance',
            description='rescue ranger!', id=sm.id)
        self.assertNotEqual(sm, sm2)

    def test_immutability(self):
        sm = contest.Staff(title="Chip'n'Dale", type='rescuer',
            description='rescue ranger!')
        self.assertRaises(AttributeError, setattr, sm, 'title', 'Hero')


@unittest.expectedFailure
class TestRaceToGoalTask(unittest.TestCase):

    def setUp(self):
        self.chps = create_checkpoints()
        self.task_id = RaceID()

    def test_incorrect_base_properties(self):
        corrupted_chps = self.chps[:]
        corrupted_chps[2] = 'Cheekpoynt'
        self.assertRaises(TypeError, contest.RaceToGoalTask, window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title='Test task', task_id=self.task_id, checkpoints=corrupted_chps)
        self.assertRaises(TypeError, contest.RaceToGoalTask, window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title='Test task', task_id=123, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.RaceToGoalTask, window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title=123, task_id=self.task_id, checkpoints=self.chps)

    def test_correct_creation(self):
        t = contest.RaceToGoalTask(window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            race_gates_number=2, race_gates_interval=15, title='Test task',
            task_id=self.task_id, checkpoints=self.chps)
        self.assertEquals(t.start_time, 1347711300)
        self.assertEquals(t.deadline, 1347732000)
        self.assertEquals(t.title, 'Test task')
        self.assertEquals(t.id, self.task_id)
        self.assertEquals(t.checkpoints, self.chps)
        self.assertEquals(t.window_open, 1347711300 + 3600)
        self.assertEquals(t.window_close, 1347711300 + 7200)
        self.assertEquals(t.race_gates_number, 2)
        self.assertEquals(t.race_gates_interval, 15)
        self.assertTrue(t.is_task_correct())

        # correst set of params with 1 race gate
        t = contest.RaceToGoalTask(window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            race_gates_number=1, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)
        self.assertEquals(t.start_time, 1347711300)
        self.assertEquals(t.deadline, 1347732000)
        self.assertEquals(t.title, 'Test task')
        self.assertEquals(t.id, self.task_id)
        self.assertEquals(t.checkpoints, self.chps)
        self.assertEquals(t.window_open, 1347711300 + 3600)
        self.assertEquals(t.window_close, 1347711300 + 7200)
        self.assertEquals(t.race_gates_number, 1)
        self.assertEquals(t.race_gates_interval, None)
        self.assertTrue(t.is_task_correct())

    def test_incorrect_window(self):
        # window bounds outwide the task
        self.assertRaises(ValueError, contest.RaceToGoalTask, window_open=1347711300 - 3600,
            window_close=1347711300 + 7200, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)
        # incorrect params: window bounds are incorrect by itself
        self.assertRaises(ValueError, contest.RaceToGoalTask, window_open=1347711300 + 3600,
            window_close=1347711300 - 3600, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)
        self.assertRaises(TypeError, contest.RaceToGoalTask, window_open='at the morning',
            window_close='when its done', title='Test task', task_id=self.task_id,
            checkpoints=self.chps)

    def test_incorrect_gates(self):
        # multiple race gates, none interval
        self.assertRaises(ValueError, contest.RaceToGoalTask, window_open=1347711300 + 3600,
            window_close=1347711300 + 7200, race_gates_number=2, title='Test task',
            task_id=self.task_id, checkpoints=self.chps)
        # one race gate, multiple intervals
        self.assertRaises(ValueError, contest.RaceToGoalTask, window_open=1347711300 + 3600,
            window_close=1347711300 + 7200, race_gates_number=1,
            race_gates_interval=10, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)

    def test_incorrect_modification(self):
        def make_correct_task():
            return contest.RaceToGoalTask(window_open=1347711300 + 3600,
                window_close=1347711300 + 7200, title='Test task', task_id=self.task_id,
                checkpoints=self.chps)
        t = make_correct_task()
        self.assertRaises(ValueError, setattr, t, 'title', 721)
        self.assertRaises(ValueError, setattr, t, 'title', '   ')
        bad_checkpoints = self.chps[:]
        bad_checkpoints[2] = '...'
        self.assertRaises(TypeError, setattr, t, 'checkpoints', bad_checkpoints)
        self.assertRaises(ValueError, setattr, t, 'checkpoints', [])

        t.race_gates_number = 1
        t.race_gates_interval = 10
        self.assertFalse(t.is_task_correct())

        t = make_correct_task()
        t.race_gates_number = 2
        t.race_gates_interval = None
        self.assertFalse(t.is_task_correct())

        t = make_correct_task()
        t.window_close = 0
        self.assertFalse(t.is_task_correct())

        t = make_correct_task()
        t.window_open = 'sometime'
        self.assertFalse(t.is_task_correct())


@unittest.expectedFailure
class TestSpeedRunTask(unittest.TestCase):

    def setUp(self):
        self.chps = create_checkpoints()
        self.task_id = RaceID()

    def test_incorrect_base_properties(self):
        corrupted_chps = self.chps[:]
        corrupted_chps[2] = 'Cheekpoynt'
        self.assertRaises(TypeError, contest.SpeedRunTask, window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title='Test task', task_id=self.task_id, checkpoints=corrupted_chps)
        self.assertRaises(TypeError, contest.SpeedRunTask, window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title='Test task', task_id=123, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.SpeedRunTask, window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title=123, task_id=self.task_id, checkpoints=self.chps)

    def test_correct_creation(self):
        t = contest.SpeedRunTask(window_open=1347711300 + 3600, window_close=1347711300 + 7200,
            title='Test task', task_id=self.task_id, checkpoints=self.chps)
        self.assertEquals(t.start_time, 1347711300)
        self.assertEquals(t.deadline, 1347732000)
        self.assertEquals(t.title, 'Test task')
        self.assertEquals(t.id, self.task_id)
        self.assertEquals(t.checkpoints, self.chps)
        self.assertEquals(t.window_open, 1347711300 + 3600)
        self.assertEquals(t.window_close, 1347711300 + 7200)
        self.assertTrue(t.is_task_correct())

    def test_incorrect_window(self):
        # window bounds outwide the task
        self.assertRaises(ValueError, contest.SpeedRunTask, window_open=1347711300 - 3600,
            window_close=1347711300 + 7200, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)
        # incorrect params: window bounds are incorrect by itself
        self.assertRaises(ValueError, contest.SpeedRunTask, window_open=1347711300 + 3600,
            window_close=1347711300 - 3600, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)
        self.assertRaises(TypeError, contest.SpeedRunTask, window_open='at the morning',
            window_close='when its done', title='Test task', task_id=self.task_id,
            checkpoints=self.chps)

    def test_incorrect_modification(self):
        def make_correct_task():
            return contest.SpeedRunTask(window_open=1347711300 + 3600,
                window_close=1347711300 + 7200, title='Test task', task_id=self.task_id,
                checkpoints=self.chps)
        t = make_correct_task()
        self.assertRaises(ValueError, setattr, t, 'title', 721)
        self.assertRaises(ValueError, setattr, t, 'title', '   ')
        bad_checkpoints = self.chps[:]
        bad_checkpoints[2] = '...'
        self.assertRaises(TypeError, setattr, t, 'checkpoints', bad_checkpoints)
        self.assertRaises(ValueError, setattr, t, 'checkpoints', [])

        t = make_correct_task()
        t.window_close = 0
        self.assertFalse(t.is_task_correct())

        t = make_correct_task()
        t.window_open = 'sometime'
        self.assertFalse(t.is_task_correct())


@unittest.expectedFailure
class TestOpenDistanceTask(unittest.TestCase):

    def setUp(self):
        self.chps = create_checkpoints()
        self.task_id = RaceID()

    def test_incorrect_base_properties(self):
        corrupted_chps = self.chps[:]
        corrupted_chps[2] = 'Cheekpoynt'
        self.assertRaises(TypeError, contest.OpenDistanceTask, bearing=1, title='Test task', task_id=self.task_id,
            checkpoints=corrupted_chps)
        self.assertRaises(TypeError, contest.OpenDistanceTask, bearing=1, title='Test task', task_id=123, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.OpenDistanceTask, bearing=1,
            title=123, task_id=self.task_id, checkpoints=self.chps)

    def test_correct_creation(self):
        t = contest.OpenDistanceTask(bearing=5, title='Test task', task_id=self.task_id,
            checkpoints=self.chps)
        self.assertEquals(t.start_time, 1347711300)
        self.assertEquals(t.deadline, 1347732000)
        self.assertEquals(t.title, 'Test task')
        self.assertEquals(t.id, self.task_id)
        self.assertEquals(t.checkpoints, self.chps)
        self.assertEquals(t.bearing, 5)
        self.assertTrue(t.is_task_correct())

    def test_incorrect_bearing(self):
        self.assertRaises(ValueError, contest.OpenDistanceTask, bearing=361,
            title='Test task', task_id=self.task_id, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.OpenDistanceTask, bearing='bear it hard',
            title='Test task', task_id=self.task_id, checkpoints=self.chps)

    def test_incorrect_modification(self):
        def make_correct_task():
            return contest.OpenDistanceTask(bearing=10, title='Test task',
                task_id=self.task_id, checkpoints=self.chps)

        t = make_correct_task()
        self.assertRaises(ValueError, setattr, t, 'title', 721)
        self.assertRaises(ValueError, setattr, t, 'title', '   ')
        bad_checkpoints = self.chps[:]
        bad_checkpoints[2] = '...'
        self.assertRaises(TypeError, setattr, t, 'checkpoints', bad_checkpoints)
        self.assertRaises(ValueError, setattr, t, 'checkpoints', [])

        t = make_correct_task()
        t.bearing = 650
        self.assertFalse(t.is_task_correct())

        t = make_correct_task()
        t.bearing = 'none'
        self.assertFalse(t.is_task_correct())


@unittest.expectedFailure
class TestContestTasks(unittest.TestCase):

    def setUp(self):
        self.cont = create_contest(1347711300 - 3600, 1347732000 + 3600)

    def _make_test_task(self, title, checkpoints):
        return contest.OpenDistanceTask(bearing=5, title=title, task_id=RaceID(),
            checkpoints=checkpoints)

    def _shift_checkpoints(self, checkpoints, shift=24 * 3600):
        # shifts each checkpoint open and close time to n seconds forward
        new_chps = []
        for chp in checkpoints:
            new_chp = chp
            if new_chp.open_time:
                new_chp.open_time += shift
            if new_chp.close_time:
                new_chp.close_time += shift
            new_chps.append(new_chp)
        return new_chps

    def test_correct_adding_one_task(self):
        t = self._make_test_task('The only task', create_checkpoints())
        self.cont.add_task(t)
        self.assertEquals(len(self.cont.tasks), 1)
        self.assertEquals(self.cont.tasks[0], t)
        self.assertEquals(self.cont.get_task(t.id), t)

    def test_add_one_violating_task(self):
        chps = create_checkpoints()
        shifted_chps = self._shift_checkpoints(chps, 1000 * 365 * 24 * 3600)
        t = self._make_test_task('Thousand years late task', shifted_chps)
        self.assertRaises(ValueError, self.cont.add_task, t)

    def test_add_not_task(self):
        self.assertRaises(TypeError, self.cont.add_task, 'hello!')

    def test_correct_modify_task(self):
        t = self._make_test_task('The only task', create_checkpoints())
        self.cont.add_task(t)
        self.cont.edit_task(t.id, title='Some other task')
        self.assertEquals(self.cont.get_task(t.id).title, 'Some other task')
        new_chps = create_checkpoints()[:-1]
        self.cont.edit_task(t.id, checkpoints=new_chps)
        self.assertEquals(self.cont.get_task(t.id).checkpoints, new_chps)

    def test_incorrect_modify_task(self):
        t = self._make_test_task('The only task', create_checkpoints())
        self.cont.add_task(t)
        self.assertRaises(ValueError, self.cont.edit_task, task_id=t.id, title='  ')
        self.assertRaises(ValueError, self.cont.edit_task, task_id=t.id,
            checkpoints=[])

    def test_correct_adding_two_tasks(self):
        self.cont.end_time += 24 * 3600
        chps = create_checkpoints()
        t1 = self._make_test_task('Task 1', chps)
        nextday_chps = self._shift_checkpoints(chps, 24 * 3600)
        t2 = self._make_test_task('Task 2', nextday_chps)

        self.cont.add_task(t1)
        self.cont.add_task(t2)
        self.assertEquals(len(self.cont.tasks), 2)
        self.assertIn(t1, self.cont.tasks)
        self.assertIn(t2, self.cont.tasks)
        self.assertEquals(self.cont.get_task(t1.id), t1)
        self.assertEquals(self.cont.get_task(t2.id), t2)

    def test_add_good_task_then_bad_task(self):
        self.cont.end_time += 24 * 3600
        chps = create_checkpoints()
        t1 = self._make_test_task('Task 1', chps)
        minutelater_chps = self._shift_checkpoints(chps, 60)
        t2 = self._make_test_task('Task 2', minutelater_chps)
        self.cont.add_task(t1)
        # overlapping
        self.assertRaises(ValueError, self.cont.add_task, t2)
        self.assertEquals(len(self.cont.tasks), 1)
        self.assertEquals(self.cont.tasks[0], t1)
        self.assertEquals(self.cont.get_task(t1.id), t1)

        # incorrect task
        t2.start_time = 'never'
        self.assertRaises(ValueError, self.cont.add_task, t2)
        self.assertEquals(len(self.cont.tasks), 1)
        self.assertEquals(self.cont.tasks[0], t1)
        self.assertEquals(self.cont.get_task(t1.id), t1)


class OrganizerTest(unittest.TestCase):
    def setUp(self):
        self.p = create_person()

    def test_creation(self):
        o = contest.Organizer(self.p.id, 'john@example.com', self.p.name,
            'big boy')
        self.assertIsInstance(o.name, Name)
        self.assertEqual(o.name, self.p.name)
        self.assertIsInstance(o.id, PersonID)
        self.assertEqual(o.id, self.p.id)
        self.assertIsInstance(o.description, str)
        self.assertEqual(o.description, 'big boy')
        self.assertIsInstance(o.email, str)
        self.assertEqual(o.email, 'john@example.com')

    def test_creation_without_description(self):
        o = contest.Organizer(self.p.id, 'john@example.com', self.p.name)
        self.assertIsInstance(o.description, str)
        self.assertEqual(o.description, '')

    def test_creation_from_strings(self):
        o = contest.Organizer(str(self.p.id), 'john@example.com', self.p.name)
        self.assertIsInstance(o.id, PersonID)
        self.assertEqual(o.id, self.p.id)

    def test_equality(self):
        o1 = contest.Organizer(self.p.id, 'john@example.com', self.p.name,
            'big boy')
        o2 = contest.Organizer(self.p.id, 'john@example.com', self.p.name,
            'big boy')
        self.assertEqual(o1, o2)

    def test_nonequality(self):
        o1 = contest.Organizer(self.p.id, 'john@example.com', self.p.name,
            'big boy')
        o2 = contest.Organizer(self.p.id, 'john@example.com', Name('Ya', "a"),
            'big boy')
        self.assertNotEqual(o1, o2)


class ParagliderTest(unittest.TestCase):
    def setUp(self):
        self.p = create_person()

    def test_creation_with_phone(self):
        p = contest.Paraglider(self.p.id, '0', ' aXis The 2', self.p.country,
            self.p.name, phone='+713')
        self.assertIsInstance(p, contest.Paraglider)
        self.assertIsInstance(p.name, Name)
        self.assertIsInstance(p.id, PersonID)
        self.assertEqual(p.id, self.p.id)
        self.assertEqual(p.name, self.p.name)
        self.assertEqual(p.contest_number, 0)
        self.assertEqual(p.glider, 'axis')
        self.assertIsInstance(p.country, Country)
        self.assertEqual(p.country, Country("UA"))
        self.assertIsInstance(p.phone, Phone)
        self.assertEqual(p.phone, Phone('+713'))

    def test_equality(self):
        p1 = contest.Paraglider(self.p.id, '0', ' aXis The 2', self.p.country,
            self.p.name, phone='+713')
        p2 = contest.Paraglider(self.p.id, '0', ' aXis The 3', self.p.country,
            self.p.name, phone='+713')
        self.assertEqual(p1, p2)

    def test_nonequality(self):
        p1 = contest.Paraglider(self.p.id, '0', ' aXis The 2', self.p.country,
            self.p.name, phone='+713')
        p2 = contest.Paraglider(PersonID(), '0', ' aXis The 2', self.p.country,
            self.p.name, phone='+713')
        self.assertNotEqual(p1, p2)

class WinddummyTest(unittest.TestCase):
    def setUp(self):
        self.p = create_person()

    def test_creation(self):
        w = contest.Winddummy(self.p.id, Phone('+7322'), self.p.name)
        self.assertIsInstance(w.id, PersonID)
        self.assertIsInstance(w.phone, Phone)
        self.assertIsInstance(w.name, Name)
        self.assertTupleEqual((w.id, w.phone, w.name),
            (self.p.id, Phone('+7322'), self.p.name))
