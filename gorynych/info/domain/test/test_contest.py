import unittest

import mock
import time
from copy import deepcopy

from gorynych.common.domain import events
from gorynych.info.domain.test.helpers import create_contest, create_person, create_transport, create_checkpoints
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
        self.assertRaises(TypeError, contest.StaffMember,
                          title='Serenity', type='ambulance',
                          description='firefly-class starship', phone=1)
        sm = contest.StaffMember(title='Millenium Falcon', type='ambulance',
                                 description='piece of junk', phone='+3456324433')
        self.assertIsInstance(sm, contest.StaffMember)
        self.assertEquals(sm.title, "Millenium Falcon")
        self.assertEquals(sm.type, "ambulance")
        self.assertEquals(sm.description, "piece of junk")
        self.assertEquals(sm.phone, '+3456324433')

class TestRaceToGoalTask(unittest.TestCase):

    def setUp(self):
        self.chps = create_checkpoints()
        self.task_id = RaceID()

    def test_incorrect_base_properties(self):
        corrupted_chps = self.chps[:]
        corrupted_chps[2] = 'Cheekpoynt'
        self.assertRaises(TypeError, contest.RaceToGoalTask,
                          window_open=1347711300 + 3600, window_close=1347711300 + 7200,
                          title='Test task', task_id=self.task_id, checkpoints=corrupted_chps)
        self.assertRaises(TypeError, contest.RaceToGoalTask,
                          window_open=1347711300 + 3600, window_close=1347711300 + 7200,
                          title='Test task', task_id=123, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.RaceToGoalTask,
                          window_open=1347711300 + 3600, window_close=1347711300 + 7200,
                          title=123, task_id=self.task_id, checkpoints=self.chps)

    def test_correct_creation(self):
        t = contest.RaceToGoalTask(window_open=1347711300 + 3600,
                                   window_close=1347711300 + 7200,
                                   race_gates_number=2,
                                   race_gates_interval=15,
                                   title='Test task',
                                   task_id=self.task_id,
                                   checkpoints=self.chps)
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
        t = contest.RaceToGoalTask(window_open=1347711300 + 3600,
                                   window_close=1347711300 + 7200,
                                   race_gates_number=1,
                                   title='Test task',
                                   task_id=self.task_id,
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
        self.assertRaises(ValueError, contest.RaceToGoalTask,
                          window_open=1347711300 - 3600,
                          window_close=1347711300 + 7200,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)
        # incorrect params: window bounds are incorrect by itself
        self.assertRaises(ValueError, contest.RaceToGoalTask,
                          window_open=1347711300 + 3600,
                          window_close=1347711300 - 3600,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)
        self.assertRaises(TypeError, contest.RaceToGoalTask,
                          window_open='at the morning',
                          window_close='when its done',
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)

    def test_incorrect_gates(self):
        # multiple race gates, none interval
        self.assertRaises(ValueError, contest.RaceToGoalTask,
                          window_open=1347711300 + 3600,
                          window_close=1347711300 + 7200,
                          race_gates_number=2,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)
        # one race gate, multiple intervals
        self.assertRaises(ValueError, contest.RaceToGoalTask,
                          window_open=1347711300 + 3600,
                          window_close=1347711300 + 7200,
                          race_gates_number=1,
                          race_gates_interval=10,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)

    def test_incorrect_modification(self):
        def make_correct_task():
            return contest.RaceToGoalTask(window_open=1347711300 + 3600,
                                          window_close=1347711300 + 7200,
                                          title='Test task',
                                          task_id=self.task_id,
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


class TestSpeedRunTask(unittest.TestCase):

    def setUp(self):
        self.chps = create_checkpoints()
        self.task_id = RaceID()

    def test_incorrect_base_properties(self):
        corrupted_chps = self.chps[:]
        corrupted_chps[2] = 'Cheekpoynt'
        self.assertRaises(TypeError, contest.SpeedRunTask,
                          window_open=1347711300 + 3600, window_close=1347711300 + 7200,
                          title='Test task', task_id=self.task_id, checkpoints=corrupted_chps)
        self.assertRaises(TypeError, contest.SpeedRunTask,
                          window_open=1347711300 + 3600, window_close=1347711300 + 7200,
                          title='Test task', task_id=123, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.SpeedRunTask,
                          window_open=1347711300 + 3600, window_close=1347711300 + 7200,
                          title=123, task_id=self.task_id, checkpoints=self.chps)

    def test_correct_creation(self):
        t = contest.SpeedRunTask(window_open=1347711300 + 3600,
                                   window_close=1347711300 + 7200,
                                   title='Test task',
                                   task_id=self.task_id,
                                   checkpoints=self.chps)
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
        self.assertRaises(ValueError, contest.SpeedRunTask,
                          window_open=1347711300 - 3600,
                          window_close=1347711300 + 7200,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)
        # incorrect params: window bounds are incorrect by itself
        self.assertRaises(ValueError, contest.SpeedRunTask,
                          window_open=1347711300 + 3600,
                          window_close=1347711300 - 3600,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)
        self.assertRaises(TypeError, contest.SpeedRunTask,
                          window_open='at the morning',
                          window_close='when its done',
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)

    def test_incorrect_modification(self):
        def make_correct_task():
            return contest.SpeedRunTask(window_open=1347711300 + 3600,
                                        window_close=1347711300 + 7200,
                                        title='Test task',
                                        task_id=self.task_id,
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


class TestOpenDistanceTask(unittest.TestCase):

    def setUp(self):
        self.chps = create_checkpoints()
        self.task_id = RaceID()

    def test_incorrect_base_properties(self):
        corrupted_chps = self.chps[:]
        corrupted_chps[2] = 'Cheekpoynt'
        self.assertRaises(TypeError, contest.OpenDistanceTask,
                          bearing=1, title='Test task', task_id=self.task_id,
                          checkpoints=corrupted_chps)
        self.assertRaises(TypeError, contest.OpenDistanceTask,
                          bearing=1, title='Test task', task_id=123, checkpoints=self.chps)
        self.assertRaises(ValueError, contest.OpenDistanceTask,
                          bearing=1, title=123, task_id=self.task_id, checkpoints=self.chps)

    def test_correct_creation(self):
        t = contest.OpenDistanceTask(bearing=5,
                                     title='Test task',
                                     task_id=self.task_id,
                                     checkpoints=self.chps)
        self.assertEquals(t.start_time, 1347711300)
        self.assertEquals(t.deadline, 1347732000)
        self.assertEquals(t.title, 'Test task')
        self.assertEquals(t.id, self.task_id)
        self.assertEquals(t.checkpoints, self.chps)
        self.assertEquals(t.bearing, 5)
        self.assertTrue(t.is_task_correct())

    def test_incorrect_bearing(self):
        self.assertRaises(ValueError, contest.OpenDistanceTask,
                          bearing=361,
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)
        self.assertRaises(ValueError, contest.OpenDistanceTask,
                          bearing='bear it hard',
                          title='Test task',
                          task_id=self.task_id,
                          checkpoints=self.chps)

    def test_incorrect_modification(self):
        def make_correct_task():
            return contest.OpenDistanceTask(bearing=10,
                                            title='Test task',
                                            task_id=self.task_id,
                                            checkpoints=self.chps)
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


class TestContestTasks(unittest.TestCase):

    def setUp(self):
        self.cont = create_contest(1347711300 - 3600, 1347732000 + 3600)

    def _make_test_task(self, title, checkpoints):
        return contest.OpenDistanceTask(bearing=5,
                                        title=title,
                                        task_id=RaceID(),
                                        checkpoints=checkpoints)

    def _shift_checkpoints(self, checkpoints, shift=24*3600):
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
        shifted_chps = self._shift_checkpoints(chps, 1000*365*24*3600)
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
        self.assertRaises(ValueError, self.cont.edit_task, task_id=t.id, checkpoints=[])

    def test_correct_adding_two_tasks(self):
        self.cont.end_time += 24*3600
        chps = create_checkpoints()
        t1 = self._make_test_task('Task 1', chps)
        nextday_chps = self._shift_checkpoints(chps, 24*3600)
        t2 = self._make_test_task('Task 2', nextday_chps)

        self.cont.add_task(t1)
        self.cont.add_task(t2)
        self.assertEquals(len(self.cont.tasks), 2)
        self.assertIn(t1, self.cont.tasks)
        self.assertIn(t2, self.cont.tasks)
        self.assertEquals(self.cont.get_task(t1.id), t1)
        self.assertEquals(self.cont.get_task(t2.id), t2)

    def test_add_good_task_then_bad_task(self):
        self.cont.end_time += 24*3600
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
