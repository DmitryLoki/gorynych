import numpy as np
import simplejson as json
from datetime import datetime

from twisted.trial import unittest

from gorynych.processor.domain import track
from gorynych.common.domain import events

test_race = json.loads('{"contest_title":"13th FAI World Paragliding Championship","country":"Bulgaria","place":"Sopot","timeoffset":"+0300","race_title":"Task 3","race_type":"racetogoal","start_time":"1374223800","end_time":"1374249600","bearing":"None","checkpoints":{"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [42.687497, 24.750131]}, "type": "Feature", "properties": {"close_time": 1374238200, "radius": 400, "name": "25S145", "checkpoint_type": "to", "open_time": 1374223800}}, {"geometry": {"type": "Point", "coordinates": [42.603923, 25.019128]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 21000, "name": "40L057", "checkpoint_type": "ss", "open_time": 1374226800}}, {"geometry": {"type": "Point", "coordinates": [42.603923, 25.019128]}, "type": "Feature", "properties": {"close_time": null, "radius": 4000, "name": "40L057", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.502614, 24.16646]}, "type": "Feature", "properties": {"close_time": null, "radius": 32000, "name": "04L055", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.504597, 25.026856]}, "type": "Feature", "properties": {"close_time": null, "radius": 5000, "name": "41P075", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.659186, 24.68335]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 2000, "name": "21L043", "checkpoint_type": "es", "open_time": 1374226800}}, {"geometry": {"type": "Point", "coordinates": [42.659186, 24.68335]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 200, "name": "21L043", "checkpoint_type": "goal", "open_time": 1374226800}}]}}')

class TestTrack(unittest.TestCase):
    def setUp(self):
        tid= track.TrackID()
        e1 = events.TrackCreated(tid,
            dict(track_type='competition_aftertask', race_task=test_race))
        self.track = track.Track(tid, [e1])

    def tearDown(self):
        del self.track

    def test_init(self):
        self.assertIsInstance(self.track, track.Track)
        self.assertEqual(self.track.state['state'], 'not started')
        self.assertEqual(self.track.type.type, 'competition_aftertask')
        self.assertEqual(self.track.task.type, 'racetogoal')

    def test_parse(self):
        self.track.append_data('1.2.609.609.igc')
        self.track.process_data()
        for ch in self.track.changes:
            print ch.name, datetime.fromtimestamp(ch.occured_on)
        print len(self.track.points)


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

    def test_dist_to_goal(self):
        rt = track.RaceToGoal(test_race)
        ts = track.TrackState([])
        c = np.ones(1, dtype=[('lat', 'f4'), ('lon', 'f4'),
            ('distance', 'i4'), ('timestamp', 'i4')])
        c[0]['lat'] = 43.9658
        c[0]['lon'] =  6.5578
        a, b = rt.process(c, ts, 15)
        self.assertTrue(a[0]['distance'] > 120000)
