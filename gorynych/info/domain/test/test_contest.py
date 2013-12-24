import json
import unittest
import time

import mock

from gorynych.common.domain import events, model, types
from gorynych.info.domain.test.helpers import create_contest, create_person, create_checkpoints
from gorynych.info.domain import contest
from gorynych.common.domain.types import Address, Name, Country, Phone, MappingCollection, Title
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
            result = contest.Organizer(pers.id, kw.get('email', pers.email),
                pers.name, kw.get('description', None))
        elif rolename.lower() == 'winddummy':
            result = contest.Winddummy(pers.id, kw['phone'], pers.name)
        else:
            raise ValueError(
                "Wrong argument passed during role creation: %s" % rolename)
    except Exception as e:
        raise unittest.SkipTest("ERROR: contest.%s can't be created: %r" % (
            rolename.capitalize(), e))
    return pers, result


class ContestFactoryTest(unittest.TestCase):
    def test_contestid_successfull_contest_creation(self):
        cont = create_contest(1, 2)
        self.assertIsInstance(cont.address, Address)
        self.assertIsInstance(cont.title, Title)
        self.assertIsInstance(cont.times, types.DateRange)
        self.assertEqual(cont.title, 'Hello world')
        self.assertEqual(cont.address, Address('Yrupinsk', 'RU', '45.23,-23.22'))
        self.assertEqual(cont.timezone, 'Europe/Moscow')
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
    def test_times_changing(self):
        cont = create_contest(1, 15)
        self.assertRaises(AttributeError, setattr, cont, 'start_time', 2)
        self.assertRaises(AttributeError, setattr, cont, 'end_time', 6)
        self.assertEqual(cont.start_time, 1)
        self.assertEqual(cont.end_time, 15)
        cont.change_times('10', '16')
        self.assertEqual((cont.start_time, cont.end_time), (10, 16))
        self.assertRaises(ValueError, cont.change_times, '10', '8')
        self.assertEqual((cont.start_time, cont.end_time), (10, 16))

    def test_times_changing_violate_contest_invariants(self):
        cont = create_contest(1, 15)
        def raiser():
            raise DomainError()
        cont.check_invariants = raiser
        self.assertEqual((1, 15), (cont.start_time, cont.end_time))
        self.assertRaises(DomainError, cont.change_times, '10', '16')

    def test_change_title(self):
        cont = create_contest(1, '15')
        cont.title = Title('  hello moOn  ')
        self.assertEqual(cont.title, 'hello moOn')

    def test_change_address(self):
        cont = create_contest(1, '15')
        cont.address = Address('Severodvinsk', 'tw', (15, 0))
        self.assertEqual(cont.address, Address('Severodvinsk', 'tw', (15, 0)))


class TaskForTests(object):
    def __init__(self, st, et, id=1, title='TestTask'):
        self.title = Title(title)
        self.window_open = int(st)
        self.deadline = int(et)
        self.id = id

    def __repr__(self):
        return str((self.window_open, self.deadline, self.id))


class TestInvariants(unittest.TestCase):
    def setUp(self):
        self.cont = create_contest(time.time(), time.time() + 3600)

    def tearDown(self):
        del self.cont

    def test_person_only_in_one_role_fail(self):
        p1 = mock.MagicMock()
        p1.id = 1
        self.cont.paragliders[1] = p1
        self.cont.staff[0] = p1
        self.cont.organizers[1] = p1
        self.assertRaises(DomainError, contest.person_only_in_one_role,
            self.cont)

    def test_person_only_in_one_role_success(self):
        self.cont.paragliders[1] = 1
        self.cont.organizers[2] = 1
        self.assertIsNone(contest.person_only_in_one_role(self.cont))

    def test_contest_times_are_good(self):
        self.assertIsNone(contest.contest_times_are_good(self.cont))
        t = mock.MagicMock()
        t.is_empty.return_value = True
        self.cont.times = t
        self.assertRaises(DomainError, contest.contest_times_are_good,
            self.cont)

    def test_task_outside_of_contest(self):
        self.cont.tasks[1] = TaskForTests(1, 2)
        self.cont.paragliders = range(2)
        try:
            contest.contest_tasks_are_correct(self.cont)
        except DomainError as e:
            self.assertTrue(e.message.startswith("Task 1 is out of contest"))

    def test_tasks_overlaps(self):
        time1 = int(time.time()) + 10
        self.cont.tasks[1] = TaskForTests(time1, time1 + 10)
        self.cont.tasks[2] = TaskForTests(time1 + 10, time1 + 20, id=2,
            title='Title2')
        self.cont.paragliders = range(3)
        try:
            contest.contest_tasks_are_correct(self.cont)
        except DomainError as e:
            self.assertTrue(e.message.startswith("Task 2 follow immediately"))

    def test_no_paragliders_for_task(self):
        self.cont.tasks[1] = TaskForTests(int(time.time()) + 10,
            int(time.time()) + 20)
        try:
            contest.contest_tasks_are_correct(self.cont)
        except DomainError as e:
            self.assertTrue(e.message.startswith("No paragliders on contest"))

    def test_contest_tasks_are_correct(self):
        time1 = int(time.time()) + 10
        t1 = TaskForTests(time1, time1 + 10)
        t2 = TaskForTests(time1 + 10, time1 + 20, id=2)
        self.cont.tasks[1] = t1
        self.cont.tasks[2] = t2
        self.cont.paragliders = range(1)
        self.assertIsNone(contest.contest_times_are_good(self.cont))


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
            _, org = create_role('organizer', self.p3, email='john@example.org')
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
        cont = contest.change_participant(self.cont, 'organizer', self.p3.id,
            email='vas@mail.ru', name=Name('Vasisualy', 'Lohankin'))
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
        self.assertIn(1, self.cont.paragliders.get_attribute_values('contest_number'))
        self.assertIn(0, self.cont.paragliders.get_attribute_values('contest_number'))

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
            type='janitor', description="Don't know who that guy is")
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


class TaskAddingTest(unittest.TestCase):
    def setUp(self):
        self.cont = create_contest(time.time(), time.time() + 3600)

    def tearDown(self):
        del self.cont


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


class _PreparedTask(unittest.TestCase):
    def setUp(self):
        self.task = mock.Mock()
        chps = json.loads(types.geojson_feature_collection(create_checkpoints()))
        self.task.checkpoints = chps
        self.task.window_open = 10
        self.task.window_close = 20
        self.task.start_time = 20
        self.task.deadline = 30

    def tearDown(self):
        del self.task


class CheckpointTypesSpecificationTest(_PreparedTask):
    def test_four_point_success(self):
        spec = contest.CheckpointTypesSpecification(['to', 'es', 'ss', 'goal'])
        self.assertTrue(spec.is_satisfied_by(self.task))

    def test_four_point_failure(self):
        spec = contest.CheckpointTypesSpecification(['to', 'es', 'ss', 'goal'])
        del self.task.checkpoints['features'][0]
        self.assertFalse(spec.is_satisfied_by(self.task))

    def test_one_point_success(self):
        spec = contest.CheckpointTypesSpecification(['to'])
        self.assertTrue(spec.is_satisfied_by(self.task))

    def test_one_point_failure(self):
        spec = contest.CheckpointTypesSpecification()
        del self.task.checkpoints['features'][0]
        self.assertFalse(spec.is_satisfied_by(self.task))


class GoalTypeSpecification(_PreparedTask):
    def test_success(self):
        self.assertTrue(contest.GoalTypeSpecification().is_satisfied_by(self.task))

    def test_no_goal(self):
        del self.task.checkpoints['features'][-1]
        self.assertFalse(contest.GoalTypeSpecification().is_satisfied_by(self.task))

    def test_wrong_goal_type(self):
        self.task.checkpoints['features'][-1]['geometry']['type'] = 'Wrong'
        self.assertFalse(contest.GoalTypeSpecification().is_satisfied_by(self.task))

    def test_new_goal_type(self):
        self.task.checkpoints['features'][-1]['geometry']['type'] = 'Line'
        self.assertTrue(contest.GoalTypeSpecification(['Point', 'Line']).is_satisfied_by(
            self.task))


class TimesSpecificationTest(_PreparedTask):
    def test_two_times(self):
        self.assertTrue(contest.TimesSpecification().is_satisfied_by(self.task))

    def test_two_times_fail(self):
        self.task.window_open = self.task.deadline
        self.assertFalse(contest.TimesSpecification(2).is_satisfied_by(self.task))

    def test_four_times(self):
        self.assertTrue(contest.TimesSpecification(4).is_satisfied_by(self.task))

    def test_four_times_fail(self):
        self.task.start_time = self.task.window_open - 1
        self.assertFalse(contest.TimesSpecification(4).is_satisfied_by(self.task))


class TasksTest(unittest.TestCase):
    '''
    It's not a test really but a fix what are tasks should be.
    '''

    def setUp(self):
        self.chps = json.loads(types.geojson_feature_collection(create_checkpoints()))
        self.id = RaceID()

    def test_opendistance(self):
        t = contest.OpenDistanceTask('Title', self.chps, 10, 20, 245, self.id)
        self._common_check(t)
        self.assertRaises(ValueError, contest.OpenDistanceTask.read_bearing,
            -1)
        self.assertIsNone(contest.OpenDistanceTask.read_bearing(None))
        self.assertEqual(0, contest.OpenDistanceTask.read_bearing(0))
        self.assertIsInstance(t.bearing, int)
        t = contest.OpenDistanceTask('Title', self.chps, 10, 20, None, self.id)
        self._common_check(t)
        self.assertIsNone(t.bearing)

    def test_racetogoal(self):
        t = contest.RaceToGoalTask('Title', self.chps, types.DateRange(10, 12),
            types.DateRange(13, 20), 1, 0, self.id)
        self._common_check(t)
        self.assertEqual(1, t.gates_number)
        self.assertEqual(0, t.gates_interval)
        self.assertEqual(t.window_close, 12)
        self.assertEqual(t.start_time, 13)

    def test_speedrun(self):
        t = contest.SpeedRunTask('Title', self.chps, types.DateRange(10, 13),
            types.DateRange(13, 20), self.id)
        self._common_check(t)
        self.assertEqual(t.window_close, 13)
        self.assertEqual(t.start_time, 13)

    def _common_check(self, t):
        self.assertIsInstance(t.id, RaceID)
        self.assertIsInstance(t.title, Title)
        self.assertIsInstance(t.checkpoints, dict)
        self.assertEqual(10, contest.OpenDistanceTask.read_bearing(10))
        self.assertEqual(t.window_open, 10)
        self.assertEqual(t.deadline, 20)


class CreatingContestTaskTest(unittest.TestCase):
    def setUp(self):
        self.cont = create_contest(1347711300 - 3600, 1347732000 + 3600)
        self.chps = json.loads(types.geojson_feature_collection(create_checkpoints()))

        class P:
            contest_number = 1

        self.cont.paragliders[1] = P()

    def test_create_racetogoal(self):
        wo = self.cont.start_time + 10
        self.cont.create_task('First', 'racetogoal', self.chps, window_open=wo,
            window_close=wo + 10, start_time=wo + 9, deadline=wo + 19,
            start_gates_interval=0, start_gates_number=1)
        self.assertIsInstance(self.cont.tasks.values()[0], contest.RaceToGoalTask)
        self.assertEqual(1, len(self.cont.tasks))

    def test_without_paragliders(self):
        wo = self.cont.start_time + 10
        self.cont.paragliders = MappingCollection()
        self.assertRaises(DomainError, self.cont.create_task, 'First',
            'racetogoal', self.chps, window_open=wo, window_close=wo + 10,
            start_time=wo + 9, deadline=wo + 19, start_gates_interval=0,
            start_gates_number=1)

    def test_create_speedrun(self):
        wo = self.cont.start_time + 10
        self.cont.create_task('First', 'speedrun', self.chps, window_open=wo,
            window_close=wo + 10, start_time=wo + 9, deadline=wo + 19)
        self.assertIsInstance(self.cont.tasks.values()[0],
            contest.SpeedRunTask)

    def test_create_opendistance(self):
        wo = self.cont.start_time + 10
        self.cont.create_task('Title', 'opendistance', self.chps,
            window_open=wo, deadline=wo + 20)
        self.assertIsInstance(self.cont.tasks.values()[0],
            contest.OpenDistanceTask)
        self.cont.create_task('Title2', 'opendistance', self.chps,
            window_open=wo + 30, deadline=wo + 40, bearing=2)


