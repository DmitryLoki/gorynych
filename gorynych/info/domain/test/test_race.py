import unittest
import uuid

import mock
from shapely.geometry import Point

from gorynych.info.domain import race
from gorynych.common.domain.types import Checkpoint


def create_race():
    pass

def create_checkpoints():
    ch1 = Checkpoint('A01', Point(42.502, 0.798), 'TO', (2, None), 2)
    ch2 = Checkpoint('A01', Point(42.502, 0.798), 'ss', (4, 6), 3)
    ch3 = Checkpoint('B02', Point(1, 2), 'es', radius=3)
    ch4 = Checkpoint('g10', Point(2, 2), 'goal', (None, 8), 3)
    return [ch1, ch2, ch3, ch4]


class RaceTest(unittest.TestCase):

    def setUp(self):
        self.race = race.Race(race.RaceID(uuid.uuid4()))
        self.race.event_publisher = mock.MagicMock()

    def tearDown(self):
        del self.race

    def test_race(self):
        self.assertIsInstance(race.RACETASKS['speedrun'](), race.SpeedRunTask)
        self.assertIsInstance(race.RACETASKS['racetogoal'](),
            race.RaceToGoalTask)
        self.assertIsInstance(race.RACETASKS['opendistance'](),
            race.OpenDistanceTask)

    def test_invariants(self):
        self.assertFalse(self.race._invariants_are_correct())
        self.race.task = race.SpeedRunTask()
        self.assertFalse(self.race._invariants_are_correct())
        self.race.paragliders[1] = 2
        self.assertFalse(self.race._invariants_are_correct())
        self.race._checkpoints.append('hoho')
        self.assertTrue(self.race._invariants_are_correct())
        self.race.task = 1
        self.assertFalse(self.race._invariants_are_correct())
        self.race.task = race.SpeedRunTask()
        self.race.paragliders = dict()
        self.assertFalse(self.race._invariants_are_correct())


    def test_set_checkpoints(self):
        # make race happy with it's invariants:
        self.race.paragliders[1] = 2
        self.race.task = race.OpenDistanceTask()
        good_checkpoints = create_checkpoints()
        self.race.checkpoints = good_checkpoints
        self.race.event_publisher.publish.assert_called_once_with(
            race.CheckpointsAreAddedToRace(self.race.id, good_checkpoints))


    def test_rollback_checkpoints(self):
        # make race happy with it's invariants:
        self.race.paragliders[1] = 2
        self.race.task = race.OpenDistanceTask()

        good_checkpoints = create_checkpoints()
        self.race.checkpoints = good_checkpoints
        self.assertEqual(self.race._checkpoints, good_checkpoints)
        try:
            self.race.checkpoints = [1, 2, 3]
        except:
            pass
        self.assertEqual(self.race._checkpoints, good_checkpoints)
        self.race.event_publisher.publish.assert_called_once_with(
            race.CheckpointsAreAddedToRace(self.race.id, good_checkpoints))


class RaceTaskTest(unittest.TestCase):
    def test_creation(self):
        task = race.RaceTask()
        self.assertIsNone(task.type)

    def test_is_checkpoints_good(self):
        task = race.RaceTask()
        chs = create_checkpoints()
        self.assertTrue(task.checkpoints_are_good(chs))
        self.assertTrue(task.checkpoints_are_good([chs[2], chs[3], chs[0],
            chs[1]]))
        self.assertRaises(ValueError, task.checkpoints_are_good, [])
        self.assertRaises(TypeError, task.checkpoints_are_good, [1, 2])




if __name__ == '__main__':
    unittest.main()
