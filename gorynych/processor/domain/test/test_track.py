import numpy as np
import simplejson as json

from twisted.trial import unittest

from gorynych.processor.domain import track
from gorynych.common.domain import events

test_race = json.loads('{"race_title":"Test Trackservice Task","race_type":"racetogoal","start_time":"1347704100","end_time":"1347724800","bearing":"None","checkpoints":{"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [43.9785, 6.48]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 1, "name": "D01", "checkpoint_type": "to", "open_time": 1347704100}}, {"geometry": {"type": "Point", "coordinates": [43.9785, 6.48]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 3000, "name": "D01", "checkpoint_type": "ss", "open_time": 1347707700}}, {"geometry": {"type": "Point", "coordinates": [44.3711, 6.3098]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 21000, "name": "B46", "checkpoint_type": "ordinal", "open_time": 1347704100}}, {"geometry": {"type": "Point", "coordinates": [43.9511, 6.3708]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 2000, "name": "B20", "checkpoint_type": "ordinal", "open_time": 1347704100}}, {"geometry": {"type": "Point", "coordinates": [44.0455, 6.3602]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 400, "name": "B43", "checkpoint_type": "ordinal", "open_time": 1347704100}}, {"geometry": {"type": "Point", "coordinates": [43.9658, 6.5578]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 1500, "name": "B37", "checkpoint_type": "es", "open_time": 1347704100}}, {"geometry": {"type": "Point", "coordinates": [43.9658, 6.5578]}, "type": "Feature", "properties": {"close_time": 1347724800, "radius": 1000, "name": "B37", "checkpoint_type": "goal", "open_time": 1347704100}}]}}')

class TestTrack(unittest.TestCase):
    def test_init(self):
        tid= track.TrackID()
        e1 = events.TrackCreated(tid,
            dict(track_type='competition_aftertask', race_task=test_race))
        t = track.Track(tid, [e1])
        self.assertIsInstance(t, track.Track)
        self.assertEqual(t.state['state'], 'not started')
        self.assertEqual(t.type.type, 'competition_aftertask')
        self.assertEqual(t.task.type, 'racetogoal')


class TestRaceToGoal(unittest.TestCase):
    def test_init(self):
        rt = track.RaceToGoal(test_race)
        self.assertIsInstance(rt, track.RaceToGoal)
        self.assertEqual(rt.type, 'racetogoal')
        self.assertTupleEqual((rt.start_time, rt.end_time), (1347704100,
                                                                1347724800))
        self.assertEqual(len(rt.checkpoints), 7)

    def test_calculate_path(self):
        rt = track.RaceToGoal(test_race)
        rt.calculate_path()
        for p in rt.checkpoints:
            print p.distance

    def test_process(self):
        rt = track.RaceToGoal(test_race)
        ts = track.TrackState([])
        c = np.ones(1, dtype=[('lat', 'f4'), ('lon', 'f4'),
            ('distance', 'i4'), ('timestamp', 'i4')])
        c[0]['lat'] = 43.9658
        c[0]['lon'] =  6.5578
        a, b = rt.process(c, ts, 15)
        self.assertTrue(a[0]['distance'] > 120000)
