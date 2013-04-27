import unittest

import mock
from shapely.geometry import Point

from gorynych.info.domain import race
from gorynych.common.domain.types import Checkpoint
from gorynych.common.exceptions import BadCheckpoint
from gorynych.info.domain.events import RaceCheckpointsChanged, ArchiveURLReceived
from gorynych.info.domain.ids import RaceID



def create_race():
    pass

def create_checkpoints():
    # also used in test_info
    ch1 = Checkpoint('A01', Point(42.502, 0.798), 'TO', (2, None), 2)
    ch2 = Checkpoint('A01', Point(42.502, 0.798), 'ss', (4, 6), 3)
    ch3 = Checkpoint('B02', Point(1, 2), 'es', radius=3)
    ch4 = Checkpoint('g10', Point(2, 2), 'goal', (None, 8), 3)
    return [ch1, ch2, ch3, ch4]


class RaceTest(unittest.TestCase):

    def setUp(self):
        self.race = race.Race(RaceID())
        self.race.event_store = mock.MagicMock()

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
        self.race.event_store.persist.assert_called_once_with(
            RaceCheckpointsChanged(self.race.id, good_checkpoints))

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
        self.race.event_store.persist.assert_called_once_with(
            RaceCheckpointsChanged(self.race.id, good_checkpoints))

    def test_get_times_from_checkpoints(self):
        ch1 = mock.Mock()
        ch1.open_time, ch1.close_time = 2, 5
        ch2 = mock.Mock()
        ch2.open_time, ch2.close_time = 4, None
        self.race._get_times_from_checkpoints([ch1, ch2])
        self.assertTupleEqual((self.race.start_time, self.race.end_time),
                              (2, 5))

    def test_get_times_from_checkpoints_bad_case(self):
        ch2 = mock.Mock()
        ch2.open_time, ch2.close_time = 4, None
        self.assertRaises(BadCheckpoint,
                          self.race._get_times_from_checkpoints, [ch2])


class RaceTrackArchiveTest(unittest.TestCase):
    def setUp(self):
        self.id = RaceID()
        r = race.Race(self.id)
        event_store = mock.Mock()
        event_store.load_events = mock.Mock()
        event_store.load_events.return_value = [1, 2]
        r.event_store = event_store
        self.r = r

    def test_track_archive(self):
        self.assertIsInstance(self.r.track_archive, race.TrackArchive)

    def test_add_track_archive(self):
        url = 'http://airtribune.com/22/asdf/tracs22-.zip'
        self.r.add_track_archive(url)
        self.r.event_store.persist.assert_called_once_with(
            ArchiveURLReceived(self.id, url))


class TrackArchiveTest(unittest.TestCase):
    def test_creation(self):
        ta = race.TrackArchive([])
        self.assertEqual(ta.state, 'new')
        self.assertEqual(ta.progress, 'nothing has been done')

    def test_apply(self):
        class AClass(object): pass
        aclass = AClass()
        ta = race.TrackArchive([])
        ta.when_aclass = mock.Mock()
        ta.apply(aclass)
        ta.when_aclass.assert_called_once_with(aclass)

    def test_creation_from_events(self):
        with mock.patch('gorynych.info.domain.race.TrackArchive.apply') as \
                        tap:
            ta = race.TrackArchive([1])
            tap.assert_called_once_with(1)

    def test_archiveurlreceived(self):
        ta = race.TrackArchive([ArchiveURLReceived(RaceID(), 'http://')])
        self.assertEqual(ta.state, 'work is started')


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
