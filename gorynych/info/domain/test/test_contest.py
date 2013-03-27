import unittest

import mock
from shapely.geometry import Point

from gorynych.info.domain import contest
from gorynych.common.domain.types import Address, Name, Country, Checkpoint
from gorynych.info.domain.tracker import TrackerID
from gorynych.info.domain.race import RaceID

def create_contest(id, start_time, end_time, title='  Hello world  ',
                   place ='Yrupinsk', country='rU', coords=(45.23, -23.22)):
    factory = contest.ContestFactory(mock.MagicMock())
    cont = factory.create_contest(id, title, start_time, end_time, place,
                                                        country, coords)
    return cont

class ContestFactoryTest(unittest.TestCase):
    def test_creation(self):
        factory = contest.ContestFactory(mock.MagicMock())
        self.assertIsInstance(factory.event_publisher, mock.MagicMock)

    def test_successfull_contest_creation(self):
        cont = create_contest(contest.ContestID('ab'), 1, 2)
        self.assertIsInstance(cont.address, Address)
        self.assertEqual(cont.title, 'Hello World')
        self.assertEquals((cont.start_time, cont.end_time), (1, 2))
        self.assertIsInstance(cont.event_publisher, mock.MagicMock)
        self.assertEqual(cont.id, contest.ContestID('ab'))

        cont = create_contest('ab', 1, 3)
        self.assertEqual(cont.end_time, 3)
        self.assertEqual(cont.id, contest.ContestID('ab'))

    def test_unsuccessfull_contest_creation(self):
        self.assertRaises(ValueError, create_contest, 1, 3, 1)


class ParagliderTest(unittest.TestCase):
    def test_success_creation(self):
        p = contest.Paraglider('1', Name('Vasya', 'Pupkin'),
                            Country('RU'), 'Mantra 9', 15, 16)
        self.assertEqual(p.person_id, '1')
        self.assertEqual(p.glider, 'mantra')
        self.assertEqual(p.contest_number, 15)
        self.assertEqual(p.tracker_id, TrackerID(16))


class ContestTest(unittest.TestCase):
    def test_register_paraglider(self):
        cont = create_contest('1', 1, 2)
        cont.register_paraglider('person1', 'mantrA 9', '747')
        self.assertEqual(len(cont._participants), 1)
        self.assertEqual(cont._participants['person1']['role'], 'paraglider')
        self.assertEqual(cont._participants['person1']['glider'], 'mantra')
        self.assertEqual(cont._participants['person1']['contest_number'], 747)

        cont.register_paraglider('person2', 'mantrA 9', '757')
        self.assertEqual(len(cont._participants), 2)
        self.assertEqual(cont._participants['person2']['role'], 'paraglider')
        self.assertEqual(cont._participants['person2']['glider'], 'mantra')
        self.assertEqual(cont._participants['person2']['contest_number'], 757)

        self.assertRaises(ValueError, cont.register_paraglider, 'person3',
            'mantrA 9', '757')

        mock_calls = cont.event_publisher.mock_calls
        # len(mock_calls) == 3 because of call.__nonzero()__ call after
        # contest creation.
        self.assertEqual(len(mock_calls), 3)
        self.assertEqual(mock_calls[-1], mock.call.publish(
            contest.ParagliderRegisteredOnContest('person2', '1')))
        self.assertEqual(mock_calls[-2], mock.call.publish(
                contest.ParagliderRegisteredOnContest('person1', '1')))

    def test_new_race(self):
        cont = create_contest('cont1', 1, 15)
        cont.register_paraglider('person2', 'mantrA 9', '757')
        cont.register_paraglider('person1', 'mantrA 9', '747')

        ch1 = Checkpoint('A01', Point(42.502, 0.798), 'TO', (2, None), 2)
        ch2 = Checkpoint('A01', Point(42.502, 0.798), 'ss', (4, 6), 3)
        ch3 = Checkpoint('B02', Point(1,2), 'es', radius=3)
        ch4 = Checkpoint('g10', Point(2,2), 'goal', (None, 8), 3)
        race = cont.new_race('Speed Run', [ch1, ch2, ch3, ch4], 'task 4')
        self.assertEqual(race.task.type, 'speedrun')
        self.assertEqual(race.checkpoints, [ch1, ch2, ch3, ch4])
        self.assertEqual(race.title, 'Task 4')
        self.assertTupleEqual((1, 15), race.timelimits)

        self.assertEqual(len(cont.races), 1)
        self.assertIsInstance(cont.races[0], RaceID)

#        self.assertEqual(len(race.paragliders), 2)


if __name__ == '__main__':
    unittest.main()