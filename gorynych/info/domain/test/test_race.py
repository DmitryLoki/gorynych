import unittest

import mock

from gorynych.common.domain.types import Name
from gorynych.info.domain.test.helpers import create_checkpoints
from gorynych.info.domain import race, contest
from gorynych.common.exceptions import BadCheckpoint
from gorynych.info.domain.events import RaceCheckpointsChanged, ArchiveURLReceived
from gorynych.info.domain.ids import RaceID, PersonID


class RaceFactoryTest(unittest.TestCase):
    def test_create_new_race(self):
        factory = race.RaceFactory()
        chs = create_checkpoints()
        pid1 = PersonID()
        pid2 = PersonID()
        rid = str(RaceID())
        pg1 = contest.Paraglider(pid1, Name("vasya", 'pupkin'), 'RU', 'gl1', '0')
        pg2 = contest.Paraglider(pid2, Name("fedya", 'pupkin'), 'RU', 'gl2',
                                 '2')
        r = factory.create_race('task 4', 'Speed Run', 'Europe/Amsterdam',
                                [pg1, pg2], chs, race_id=rid)

        self.assertEqual(r.type, 'speedrun')
        self.assertEqual(r.checkpoints, chs)
        self.assertEqual(r.title, 'Task 4')
        self.assertEqual(r.timezone, 'Europe/Amsterdam')
        self.assertTupleEqual((r.start_time, r.end_time),
                              (1347711300, 1347732000))
        self.assertIsNone(r.bearing)
        self.assertIsNone(r._id)
        self.assertIsInstance(r.id, RaceID)
        self.assertEqual(r.id,  RaceID.fromstring(rid))

        self.assertEqual(len(r.paragliders), 2)
        p1 = r.paragliders['0']
        p2 = r.paragliders['2']
        self.assertTupleEqual(
            (p1.person_id, p1.country, p1.glider, p1.contest_number, p1.name),
            (pid1, 'RU', 'gl1', '0', 'V. Pupkin'))
        self.assertTupleEqual(
            (p2.person_id, p2.country, p2.glider, p2.contest_number, p2.name),
            (pid2, 'RU', 'gl2', '2', 'F. Pupkin'))

class RaceTest(unittest.TestCase):

    def setUp(self):
        self.race = race.Race(RaceID())

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

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_set_checkpoints(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store
        # make race happy with it's invariants:
        self.race.paragliders[1] = 2
        self.race.task = race.OpenDistanceTask()
        good_checkpoints = create_checkpoints()
        self.race.checkpoints = good_checkpoints
        assert not event_store.persist.called, "Event was fired but " \
                                               "shouldn't be."

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_rollback_checkpoints(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store
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
        assert not event_store.persist.called, "Event was fired but " \
                                               "shouldn't be."

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


class RaceTrackArchiveTest(unittest.TestCase):
    def setUp(self):
        raise unittest.SkipTest("Work hasn't finished yet.")
        self.id = RaceID()
        r = race.Race(self.id)
        event_store = mock.Mock()
        event_store.load_events = mock.Mock()
        event_store.load_events.return_value = [1, 2]
        self.r = r
        self.event_store = event_store

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_track_archive(self, patched):
        patched.return_value = self.event_store
        self.assertIsInstance(self.r.track_archive, race.TrackArchive)

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_add_track_archive(self, patched):
        patched.return_value = self.event_store
        url = 'http://airtribune.com/22/asdf/tracs22-.zip'
        self.r.add_track_archive(url)
        self.event_store.persist.assert_called_once_with(
            ArchiveURLReceived(self.id, url))


class TrackArchiveTest(unittest.TestCase):
    def setUp(self):
        raise unittest.SkipTest("Work hasn't finished yet.")

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


