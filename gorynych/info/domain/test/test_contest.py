import uuid
import unittest

import mock
from shapely.geometry import Point

from gorynych.info.domain import contest, person
from gorynych.common.domain.types import Address, Name, Country, Checkpoint
from gorynych.info.domain.events import ParagliderRegisteredOnContest
from gorynych.info.domain.ids import RaceID


def create_contest(start_time, end_time, id=None,
                   title='  Hello world  ',
                   place='Yrupinsk', country='rU', coords=(45.23, -23.22),
                   timezone='Europe/Moscow'):
    factory = contest.ContestFactory()
    cont = factory.create_contest(title, start_time, end_time, place,
        country, coords, timezone, id)
    if not id:
        id = cont.id
    return cont, id


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
        cont, cont_id = create_contest(1, 2)
        self.assertIsInstance(cont.address, Address)
        self.assertEqual(cont.title, 'Hello World')
        self.assertEqual(cont.country, 'RU')
        self.assertEqual(cont.timezone, 'Europe/Moscow')
        self.assertEqual(cont.place, 'Yrupinsk')
        self.assertEquals((cont.start_time, cont.end_time), (1, 2))
        self.assertIsInstance(cont.id, contest.ContestID)
        self.assertIsNone(cont._id)

        cont2, cont_id2 = create_contest(3, 4)
        self.assertNotEqual(cont_id, cont_id2, "Contest with the same id has"
                                               " been created.")

    def test_str_successfull_contest_creation(self):
        cont, cont_id = create_contest(1, 3, id='cnts-130422-12345')
        self.assertEqual(cont.end_time, 3)
        self.assertEqual(cont.start_time, 1)
        self.assertEqual(cont.id, 'cnts-130422-12345')

    def test_unsuccessfull_contest_creation(self):
        self.assertRaises(ValueError, create_contest, 3, 1,
                          "Contest can be created with wrong times.")


class ParagliderTest(unittest.TestCase):
    def test_success_creation(self):
        p_id = str(uuid.uuid4())
        p = contest.Paraglider(p_id, Name('Vasya', 'Pupkin'),
            Country('RU'), 'Mantra 9', 15, 16)
        self.assertEqual(p.person_id, p_id)
        self.assertEqual(p.glider, 'mantra')
        self.assertEqual(p.contest_number, 15)
        # TODO: uncomment then TrackerID will be implemented.
        # self.assertEqual(p.tracker_id, TrackerID())


class ContestTest(unittest.TestCase):
    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_register_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store
        cont, cont_id = create_contest(1, 2)
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
            ParagliderRegisteredOnContest(p2, cont_id)))
        self.assertEqual(mock_calls[-2], mock.call.persist(
            ParagliderRegisteredOnContest(p1, cont_id)))


    def test_times_changing(self):
        cont, cont_id = create_contest(1, '15')
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
        cont, cont_id = create_contest(1, '15')
        cont.title = '  hello moOn  '
        self.assertEqual(cont.title, 'Hello Moon')

    def test_change_address(self):
        cont, cont_id = create_contest(1, '15')
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
            cont, cont_id = create_contest(1, 15)
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

    @mock.patch('gorynych.common.infrastructure.persistence.get_repository')
    def test_new_race(self, patched):
        patched.return_value = MockedPersonRepository()
        # cont, cont_id = create_contest(1, 15)
        # cont.register_paraglider(self.p2_id, 'mantrA 9', '757')
        # cont.register_paraglider(self.p1_id, 'gIn 9', '747')
        # person without tracker
        # cont.register_paraglider(self.p3_id, 'gIn 9', '777')

        ch1 = Checkpoint('A01', Point(42.502, 0.798), 'TO', (2, None), 2)
        ch2 = Checkpoint('A01', Point(42.502, 0.798), 'ss', (4, 6), 3)
        ch3 = Checkpoint('B02', Point(1, 2), 'es', radius=3)
        ch4 = Checkpoint('g10', Point(2, 2), 'goal', (None, 8), 3)
        race = self.cont.new_race('Speed Run', [ch1, ch2, ch3, ch4], 'task 4')

        ### test Race aggregate ###
        self.assertEqual(race.type, 'speedrun')
        self.assertEqual(race.checkpoints, [ch1, ch2, ch3, ch4])
        self.assertEqual(race.title, 'Task 4')
        self.assertTupleEqual((1, 15), race.timelimits)
        self.assertTupleEqual((race.start_time, race.end_time), (2, 8))
        self.assertEqual(race.timezone, self.cont.timezone)
        self.assertIsNone(race.bearing)

        ### test Contest aggregate ###
        self.assertEqual(len(self.cont.race_ids), 1)
        self.assertIsInstance(self.cont.race_ids[0], RaceID)

        self.assertEqual(len(race.paragliders), 2)
        p1 = race.paragliders[747]
        p2 = race.paragliders[757]
        self.assertEqual((str(p1.person_id), p1.name,
                          p1.glider,
                          p1.country),
            (self.p1_id, 'N. Surname', 'gin', 'RU'))
        self.assertEqual((str(p2.person_id), p2.name,
                          p2.glider,
                          p2.country),
            (self.p2_id, 'N. Surname', 'mantra', 'RU'))


if __name__ == '__main__':
    unittest.main()

