import unittest

import mock
from shapely.geometry import Point

from gorynych.info.domain import race
from gorynych.common.domain.types import Checkpoint
from gorynych.common.exceptions import BadCheckpoint


def create_checkpoints():
    # also used in test_info
    ch1 = Checkpoint('D01', Point(43.9785, 6.48), 'TO',
                     (1347711300, 1347716700), 1)
    ch2 = Checkpoint('D01', Point(43.9785, 6.48), 'ss',
                     (1347714900, 1347732000), 3000)
    ch2_ordinal = Checkpoint('B20', Point(43.9511, 6.3708),  radius=2000)
    ch3 = Checkpoint('B37', Point(43.9658, 6.5578), 'es',
                     (1347714900, 1347732000), radius=1500)
    ch4 = Checkpoint('g10', Point(43.9658, 6.5578), 'goal',
                     (1347714900, 1347732000), 1000)
    return [ch1, ch2, ch2_ordinal, ch3, ch4]


class RaceTest(unittest.TestCase):

    def setUp(self):
        self.race = race.Race(race.RaceID())
        self.race.event_publisher = mock.MagicMock()

    def tearDown(self):
        del self.race

    def test_race_module(self):
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

    def test_get_times_from_checkpoints(self):
        chs = create_checkpoints()
        self.race._get_times_from_checkpoints(chs)
        self.assertTupleEqual((self.race.start_time, self.race.end_time),
                              (1347711300, 1347732000))

    def test_get_times_from_checkpoints_bad_case(self):
        ch2 = mock.Mock()
        ch2.open_time, ch2.close_time = 4, None
        self.assertRaises(BadCheckpoint,
                          self.race._get_times_from_checkpoints, [ch2])


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
