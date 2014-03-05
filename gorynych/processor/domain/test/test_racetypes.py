from twisted.trial import unittest
import types

import mock
import numpy as np

from zope.interface.verify import verifyObject
from gorynych.processor.interfaces import IRaceType

from gorynych.processor.domain import track
from gorynych.processor.domain import racetypes
from gorynych.common.domain import events
from gorynych.common.domain.model import DomainEvent
from gorynych.processor.domain.racetypes import RaceTypesFactory


class CheckpointAdapter(object):

    def __init__(self, chp, error_margin):
        self._point_inside = False
        self.checkpoint = chp
        self.error_margin = error_margin


def create_checkpoint_adapter(lat=40.1, lon=40.2, error_margin=50,
                              radius=100):
    chp = mock.Mock()
    chp.lat, chp.lon, chp.radius = lat, lon, radius

    result = CheckpointAdapter(chp, error_margin)
    return result


test_race = {
    "contest_title": "Some contest",
    "properties": {
        "window_open": 1374223800,
        "window_close": 1374238200,
        "start_time": 1374226800,
        "deadline": 1374249600,
        "bearing": None
    },
    "country": "Some country",
    "place": "Some place",
    "timeoffset": "+0300",
    "race_title": "Some task",
    "type": "racetogoal",
    "checkpoints": {
        "type": "FeatureCollection",
        "features": [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [1, 1]
                    },
                    "type": "Feature",
                    "properties": {
                        "close_time": 1374238200,
                        "radius": 10,
                        "name": "1",
                        "checkpoint_type": "to",
                        "open_time": 1374223800
                    }
                },
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [2, 2]
                },
                "type": "Feature",
                "properties": {
                        "close_time": 1374249600,
                        "radius": 10,
                        "name": "2",
                        "checkpoint_type": "ss",
                        "open_time": 1374226800
                }
            },
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [3, 3]
                },
                "type": "Feature",
                "properties": {
                        "close_time": None,
                        "radius": 10,
                        "name": "3",
                        "checkpoint_type": "ordinal",
                        "open_time": None
                }
            },
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [4, 4]
                },
                "type": "Feature",
                "properties": {
                        "close_time": None,
                        "radius": 10,
                        "name": "4",
                        "checkpoint_type": "ordinal",
                        "open_time": None
                }
            },
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [5, 5]
                },
                "type": "Feature",
                "properties": {
                        "close_time": None,
                        "radius": 10,
                        "name": "5",
                        "checkpoint_type": "ordinal",
                        "open_time": None
                }
            },
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [6, 6]
                },
                "type": "Feature",
                "properties": {
                        "close_time": 1374249600,
                        "radius": 10,
                        "name": "6",
                        "checkpoint_type": "es",
                        "open_time": 1374226800
                }
            },
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [7, 7]
                },
                "type": "Feature",
                "properties": {
                        "close_time": 1374249600,
                        "radius": 10,
                        "name": "7",
                        "checkpoint_type": "goal",
                        "open_time": 1374226800
                }
            }
        ]
    }
}


def make_pilot_points(rc):
    """
    Points of pilot's track: for testing purposes we just assume that he/she teleports
    from one checkpoint center to another.
    """
    count = len(rc['checkpoints']['features'])
    teleportation_steps = np.ones(count,
                                  dtype=[('lat', 'f4'), ('lon', 'f4'),
                                         ('distance', 'i4'), ('timestamp', 'i4')])
    mintime = [chp for chp in rc['checkpoints']['features'] if
               chp['properties']['checkpoint_type'] == 'to'][0]['properties']['open_time']
    maxtime = [chp for chp in rc['checkpoints']['features'] if
               chp['properties']['checkpoint_type'] == 'goal'][0]['properties']['close_time']
    timescale = np.linspace(mintime, maxtime, count)
    for i, (step, checkpoint) in enumerate(zip(teleportation_steps, rc['checkpoints']['features'])):
        step['lat'] = checkpoint['geometry']['coordinates'][0]
        step['lon'] = checkpoint['geometry']['coordinates'][1]
        step['timestamp'] = timescale[i]
    return teleportation_steps


class TestTakenOnExit(unittest.TestCase):

    def setUp(self):
        adapter = create_checkpoint_adapter()
        adapter.taken = types.MethodType(racetypes.taken_on_exit,
                                         adapter, CheckpointAdapter)
        self.adapter = adapter

    def tearDown(self):
        del self.adapter

    def test_point_outside(self):
        result = self.adapter.taken(41, 41, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertFalse(result)

    def test_point_inside(self):
        result = self.adapter.taken(40.1, 40.2, 15)
        self.assertTrue(self.adapter._point_inside)
        self.assertEqual(self.adapter.take_time, 15)
        self.assertFalse(result)

    def test_point_still_inside(self):
        self.adapter._point_inside = True
        result = self.adapter.taken(40.1, 40.2, 15)
        self.assertTrue(self.adapter._point_inside)
        self.assertEqual(self.adapter.take_time, 15)
        self.assertFalse(result)

    def test_point_outside_again(self):
        self.adapter._point_inside = True
        result = self.adapter.taken(41, 42, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertRaises(AttributeError, getattr, self.adapter, 'take_time')
        self.assertTrue(result)


class TestTakenOnEnter(unittest.TestCase):

    def setUp(self):
        adapter = create_checkpoint_adapter()
        adapter.taken = types.MethodType(racetypes.taken_on_enter,
                                         adapter, CheckpointAdapter)
        self.adapter = adapter

    def tearDown(self):
        del self.adapter

    def test_point_outside(self):
        result = self.adapter.taken(41, 41, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertFalse(result)

    def test_point_taken(self):
        result = self.adapter.taken(40.1, 40.2, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertTrue(result)
        self.assertEqual(self.adapter.take_time, 15)


class TestRaceTypesFactoryCreate(unittest.TestCase):

    def setUp(self):
        factory = racetypes.RaceTypesFactory()
        self.checkpoint_factory = mock.patch(
            'gorynych.processor.domain'
            '.racetypes.checkpoint_collection_from_geojson')
        self.checkpoint_factory.start()
        self.services = mock.patch(
            'gorynych.processor.domain.services.JavaScriptShortWay')
        self.services.start()
        self.factory = factory

    def tearDown(self):
        self.checkpoint_factory.stop()
        self.services.stop()

    def test_no_race_type(self):
        rtask = dict(rac_type='racetogoal')
        self.assertRaises(ValueError, self.factory.create, 'online', rtask)

    def test_no_race(self):
        rtask = dict(race_type='unknown')
        self.assertRaises(ValueError, self.factory.create, 'online', rtask)


class RaceTestCase(unittest.TestCase):

    """
    Common TestCase class for all the racetypes.
    """

    def _check_format(self, evlist, pts):
        # event list
        self.assertIsInstance(evlist, list)
        for ev in evlist:
            self.assertIsInstance(ev, DomainEvent)
            self.assertEqual(getattr(ev, 'aggregate_type'), 'track')
            self.assertEqual(getattr(ev, 'aggregate_id'), self.track_id)

        # points
        self.assertIsInstance(pts, np.ndarray)
        for point in pts:
            self.assertIsInstance(point['lat'], np.float32)
            self.assertIsInstance(point['lon'], np.float32)
            self.assertIsInstance(point['timestamp'], np.int32)
            self.assertIsInstance(point['distance'], np.int32)

    def _check_distance(self, pts, dists):
        for point, dst in zip(pts, dists):
            self.assertEqual(point['distance'], dst)

    def _check_taken_checkpoints(self, evlist):
        for i, ev in enumerate(evlist, start=1):
            self.assertEqual((i, 0), getattr(ev, 'payload'))
            self.assertEqual(getattr(ev, 'occured_on'),
                             self.complete_track[i]['timestamp'])

    def assertTrackIsComplete(self, pts, evlist):
        # first 6 checkpoints must be taken (except TakeOff)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 6)
        self._check_taken_checkpoints(chp_taken)

        # then there must be one TrackStarted
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)
        self.assertEqual(getattr(trk_started[0], 'occured_on'),
                         self.complete_track[1]['timestamp'])

        # one TrackFinishTimeReceived
        trk_ftime = [ev for ev in evlist if
                     isinstance(ev, events.TrackFinishTimeReceived)]
        self.assertEqual(len(trk_ftime), 1)
        self.assertEqual(getattr(trk_ftime[0], 'payload'),
                         self.complete_track[-2]['timestamp'])

        # one TrackFinished
        trk_fin = [ev for ev in evlist if isinstance(ev, events.TrackFinished)]
        self.assertEqual(len(trk_fin), 1)


class TestRaceToGoal(RaceTestCase):

    def setUp(self):
        self.factory = RaceTypesFactory()
        self.test_race = test_race.copy()
        self.complete_track = make_pilot_points(self.test_race)
        self.rt = self.factory.create('online', self.test_race)
        self.track_id = track.TrackID()
        self.ts = track.TrackState(self.track_id, [])

    def test_init(self):
        self.assertIsInstance(self.rt, racetypes.RaceToGoal)
        self.assertTrue(verifyObject(IRaceType, self.rt))
        self.assertEqual(self.rt.type, 'racetogoal')
        self.assertTupleEqual(
            (self.rt.start_time, self.rt.end_time), (1374223800,
                                                     1374249600))
        self.assertEqual(len(self.rt.checkpoints), 7)

    def test_dist_to_goal(self):
        c = np.ones(1, dtype=[('lat', 'f4'), ('lon', 'f4'),
                   ('distance', 'i4'), ('timestamp', 'i4')])
        c[0]['lat'] = 43.9658
        c[0]['lon'] = 6.5578
        a, b = self.rt.process(c, self.ts, self.track_id)
        self.assertTrue(a[0]['distance'] > 120000)

    def test_successful_track(self):
        pts, evlist = self.rt.process(
            self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [942144, 784919, 627742, 470637, 313627, 156737, 9])
        self.assertTrackIsComplete(pts, evlist)

    def test_one_checkpoint_missing(self):
        malformed_track = np.delete(self.complete_track, 3)
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [942144, 784919, 627742, 627667, 784557, 941304])
        self.assertEqual(len(evlist), 3)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinishTimeReceived)]))
        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinished)]))
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)

    def test_two_checkpoints_missing(self):
        malformed_track = np.delete(self.complete_track, [3, 5])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [942144, 784919, 627742, 627667, 941304])
        self.assertEqual(len(evlist), 3)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinishTimeReceived)]))
        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinished)]))
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)

    def test_start_missing(self):
        malformed_track = np.delete(self.complete_track, [1, 2])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self.assertEqual(evlist, [])

    def test_takeoff_missing(self):
        malformed_track = self.complete_track[1:]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [784919, 627742, 470637, 313627, 156737, 9])
        self.assertTrackIsComplete(pts, evlist)

    def test_goal_missing(self):
        malformed_track = self.complete_track[:-1]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [942144, 784919, 627742, 470637, 313627, 156737])
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 5)
        self._check_taken_checkpoints(chp_taken)

        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)
        self.assertEqual(getattr(trk_started[0], 'occured_on'),
                         self.complete_track[1]['timestamp'])

        trk_ftime = [ev for ev in evlist if
                     isinstance(ev, events.TrackFinishTimeReceived)]
        self.assertEqual(len(trk_ftime), 1)
        self.assertEqual(getattr(trk_ftime[0], 'payload'),
                         self.complete_track[-2]['timestamp'])

        # there has to be no TrackFinished
        trk_fin = [ev for ev in evlist if isinstance(ev, events.TrackFinished)]
        self.assertEqual(len(trk_fin), 0)

    def test_unfinished_task(self):
        malformed_track = self.complete_track[:3]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [942144, 784919, 627742])
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)
        self.assertEqual(getattr(trk_started[0], 'occured_on'),
                         self.complete_track[1]['timestamp'])
        trk_ftime = [ev for ev in evlist if
                     isinstance(ev, events.TrackFinishTimeReceived)]
        self.assertEqual(len(trk_ftime), 0)

        # there has to be no TrackFinished
        trk_fin = [ev for ev in evlist if isinstance(ev, events.TrackFinished)]
        self.assertEqual(len(trk_fin), 0)

    def test_one_point(self):
        self.ts.last_checkpoint = 6
        pts, evlist = self.rt.process(self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [200, 200, 200, 200, 200, 200, 200])
        self.assertEqual(len(evlist), 0)

    def test_overcomplete_track(self):

        malformed_track = np.append(self.complete_track, self.complete_track[::-1])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        final_distance = pts[6]['distance']
        for point in pts[7:]:
            self.assertEqual(point['distance'], final_distance)

    test_overcomplete_track.todo = 'Class is not corrected yet'


class TestSpeedRun(RaceTestCase):

    def setUp(self):
        self.factory = RaceTypesFactory()
        self.test_race = test_race.copy()
        self.test_race['type'] = 'speedrun'
        self.complete_track = make_pilot_points(self.test_race)
        self.rt = self.factory.create('online', self.test_race)
        self.track_id = track.TrackID()
        self.ts = track.TrackState(self.track_id, [])

    def tearDown(self):
        del self.test_race
        del self.rt
        del self.ts

    def test_init(self):
        self.assertIsInstance(self.rt, racetypes.SpeedRun)
        self.assertTrue(verifyObject(IRaceType, self.rt))
        self.assertEqual(self.rt.type, 'speedrun')
        self.assertTupleEqual(
            (self.rt.start_time, self.rt.end_time), (1374223800,
                                                     1374249600))
        self.assertEqual(len(self.rt.checkpoints), 7)

    def test_dist_to_goal(self):
        c = np.ones(1, dtype=[('lat', 'f4'), ('lon', 'f4'),
                   ('distance', 'i4'), ('timestamp', 'i4')])
        c[0]['lat'] = 43.9658
        c[0]['lon'] = 6.5578
        a, b = self.rt.process(c, self.ts, self.track_id)
        self.assertTrue(a[0]['distance'] > 120000)

    def test_successful_track(self):
        pts, evlist = self.rt.process(
            self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [314420, 471549, 628582, 785497, 942267, 1098871, 942143])
        self.assertTrackIsComplete(pts, evlist)

    def test_one_checkpoint_missing(self):
        malformed_track = np.delete(self.complete_track, 3)
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [314420, 471549, 628582, 628507, 785397, 942144])
        self.assertEqual(len(evlist), 3)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinishTimeReceived)]))
        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinished)]))
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)

    def test_two_checkpoints_missing(self):
        malformed_track = np.delete(self.complete_track, [3, 5])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [314420, 471549, 628582, 628507, 942144])
        self.assertEqual(len(evlist), 3)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinishTimeReceived)]))
        self.assertFalse(any([ev for ev in evlist if
                              isinstance(ev, events.TrackFinished)]))
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)

    def test_start_missing(self):
        malformed_track = np.delete(self.complete_track, [1, 2])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self.assertEqual(evlist, [])

    def test_takeoff_missing(self):
        malformed_track = self.complete_track[1:]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [471549, 628582, 785497, 942267, 1098871, 942143])
        self.assertTrackIsComplete(pts, evlist)

    def test_goal_missing(self):
        malformed_track = self.complete_track[:-1]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [314420, 471549, 628582, 785497, 942267, 1098871])
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 5)
        self._check_taken_checkpoints(chp_taken)

        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)
        self.assertEqual(getattr(trk_started[0], 'occured_on'),
                         self.complete_track[1]['timestamp'])

        trk_ftime = [ev for ev in evlist if
                     isinstance(ev, events.TrackFinishTimeReceived)]
        self.assertEqual(len(trk_ftime), 1)
        self.assertEqual(getattr(trk_ftime[0], 'payload'),
                         self.complete_track[-2]['timestamp'])

        # there has to be no TrackFinished
        trk_fin = [ev for ev in evlist if isinstance(ev, events.TrackFinished)]
        self.assertEqual(len(trk_fin), 0)

    def test_unfinished_task(self):
        malformed_track = self.complete_track[:3]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [314420, 471549, 628582])
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)
        trk_started = [ev for ev in evlist if
                       isinstance(ev, events.TrackStarted)]
        self.assertEqual(len(trk_started), 1)
        self.assertEqual(getattr(trk_started[0], 'occured_on'),
                         self.complete_track[1]['timestamp'])
        trk_ftime = [ev for ev in evlist if
                     isinstance(ev, events.TrackFinishTimeReceived)]
        self.assertEqual(len(trk_ftime), 0)

        # there has to be no TrackFinished
        trk_fin = [ev for ev in evlist if isinstance(ev, events.TrackFinished)]
        self.assertEqual(len(trk_fin), 0)

    def test_one_point(self):
        self.ts.last_checkpoint = 6
        pts, evlist = self.rt.process(self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [200, 200, 200, 200, 200, 200, 200])
        self.assertEqual(len(evlist), 0)
    
    def test_overcomplete_track(self):

        malformed_track = np.append(self.complete_track, self.complete_track[::-1])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        final_distance = pts[6]['distance']
        for point in pts[7:]:
            self.assertEqual(point['distance'], final_distance)

    test_overcomplete_track.todo = 'Class is not corrected yet'
        

class TestOpenDistance(RaceTestCase):

    def setUp(self):
        self.factory = RaceTypesFactory()
        self.test_race = test_race.copy()
        self.test_race['type'] = 'opendistance'
        self.complete_track = make_pilot_points(self.test_race)
        self.rt = self.factory.create('online', self.test_race)
        self.track_id = track.TrackID()
        self.ts = track.TrackState(self.track_id, [])

    def test_init(self):
        self.assertIsInstance(self.rt, racetypes.OpenDistance)
        self.assertTrue(verifyObject(IRaceType, self.rt))
        self.assertEqual(self.rt.type, 'opendistance')
        self.assertTupleEqual(
            (self.rt.start_time, self.rt.end_time), (1374223800,
                                                     1374249600))
        self.assertEqual(len(self.rt.checkpoints), 7)

    def test_dist_to_goal(self):
        c = np.ones(1, dtype=[('lat', 'f4'), ('lon', 'f4'),
                   ('distance', 'i4'), ('timestamp', 'i4')])
        c[0]['lat'] = 43.9658
        c[0]['lon'] = 6.5578
        a, b = self.rt.process(c, self.ts, self.track_id)
        self.assertTrue(a[0]['distance'] > 120000)

    def test_successful_track(self):
        pts, evlist = self.rt.process(
            self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [10, 157215, 471597, 785880, 1099995, 1413894, 785396])
        self.assertEqual(len(evlist), 6)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 6)
        self._check_taken_checkpoints(chp_taken)

    def test_one_checkpoint_missing(self):
        malformed_track = np.delete(self.complete_track, 3)
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [10, 157215, 471597, 942890, 1099779, 1256524])
        self.assertEqual(len(evlist), 2)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

    def test_two_checkpoints_missing(self):
        malformed_track = np.delete(self.complete_track, [3, 5])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [10, 157215, 471597, 942890, 1256524])
        self.assertEqual(len(evlist), 2)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

    def test_start_missing(self):
        malformed_track = np.delete(self.complete_track, [1, 2])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self.assertEqual(evlist, [])

    def test_takeoff_missing(self):
        malformed_track = self.complete_track[1:]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [157215, 471597, 785880, 1099995, 1413894, 785395])
        self.assertEqual(len(evlist), 6)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 6)
        self._check_taken_checkpoints(chp_taken)

    def test_goal_missing(self):
        malformed_track = self.complete_track[:-1]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [10, 157215, 471597, 785880, 1099995, 1413894])
        self.assertEqual(len(evlist), 5)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 5)
        self._check_taken_checkpoints(chp_taken)

    def test_unfinished_task(self):
        malformed_track = self.complete_track[:3]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [10, 157215, 471597])
        self.assertEqual(len(evlist), 2)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

    def test_one_point(self):
        self.ts.last_checkpoint = 6
        pts, evlist = self.rt.process(self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [1884276, 1727052, 1569876, 1412771, 1255762, 1098871, 942143])
        self.assertEqual(len(evlist), 0)

    def test_successful_track_with_bearing(self):
        self.test_race['properties']['bearing'] = 20
        self.rt = self.factory.create('online', self.test_race)
        pts, evlist = self.rt.process(
            self.complete_track, self.ts, self.track_id)
        self._check_format(evlist, pts)
        self._check_distance(pts, [10, 157215, 471597, 785880, 1099995, 1413894, 785395])
        self.assertEqual(len(evlist), 6)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 6)
        self._check_taken_checkpoints(chp_taken)

if __name__ == '__main__':
    unittest.main()
