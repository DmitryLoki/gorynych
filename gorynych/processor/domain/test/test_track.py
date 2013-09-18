import numpy as np
import simplejson as json
from datetime import datetime

from twisted.trial import unittest
from gorynych.processor.domain.racetypes import RaceToGoal, RaceTypesFactory

from gorynych.processor.domain import track
from gorynych.common.domain import events
from gorynych.common.domain.model import DomainEvent

test_race = json.loads(
    '{"contest_title":"13th FAI World Paragliding Championship","country":"Bulgaria","place":"Sopot","timeoffset":"+0300","race_title":"Task 3","race_type":"racetogoal","start_time":"1374223800","end_time":"1374249600","bearing":"None","checkpoints":{"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [42.687497, 24.750131]}, "type": "Feature", "properties": {"close_time": 1374238200, "radius": 400, "name": "25S145", "checkpoint_type": "to", "open_time": 1374223800}}, {"geometry": {"type": "Point", "coordinates": [42.603923, 25.019128]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 21000, "name": "40L057", "checkpoint_type": "ss", "open_time": 1374226800}}, {"geometry": {"type": "Point", "coordinates": [42.603923, 25.019128]}, "type": "Feature", "properties": {"close_time": null, "radius": 4000, "name": "40L057", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.502614, 24.16646]}, "type": "Feature", "properties": {"close_time": null, "radius": 32000, "name": "04L055", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.504597, 25.026856]}, "type": "Feature", "properties": {"close_time": null, "radius": 5000, "name": "41P075", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.659186, 24.68335]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 2000, "name": "21L043", "checkpoint_type": "es", "open_time": 1374226800}}, {"geometry": {"type": "Point", "coordinates": [42.659186, 24.68335]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 200, "name": "21L043", "checkpoint_type": "goal", "open_time": 1374226800}}]}}')


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

th_fai_1_task = json.loads(
    '{"contest_title":"12th  FAI European Paragliding Championship","country":"France","place":"Saint andre les alpes","timeoffset":"+0200","race_title":"Task 1 - 103 km","race_type":"racetogoal","start_time":"1346924700","end_time":"1346949000","bearing":"None","checkpoints":{"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [43.9785, 6.48]}, "type": "Feature", "properties": {"close_time": 1346930100, "radius": 1, "name": "D01", "checkpoint_type": "to", "open_time": 1346924700}}, {"geometry": {"type": "Point", "coordinates": [43.9388333333, 6.4078333333]}, "type": "Feature", "properties": {"close_time": 1346949000, "radius": 5000, "name": "B40", "checkpoint_type": "ss", "open_time": 1346928300}}, {"geometry": {"type": "Point", "coordinates": [44.4063333333, 6.2163333333]}, "type": "Feature", "properties": {"close_time": null, "radius": 20000, "name": "B13", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [43.7578333333, 6.6238333333]}, "type": "Feature", "properties": {"close_time": null, "radius": 20000, "name": "B15", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [43.9878333333, 6.3643333333]}, "type": "Feature", "properties": {"close_time": null, "radius": 1000, "name": "B42", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [43.9658333333, 6.5578333333]}, "type": "Feature", "properties": {"close_time": 1346949000, "radius": 1000, "name": "B37", "checkpoint_type": "es", "open_time": 1346928300}}, {"geometry": {"type": "Point", "coordinates": [43.9586666667, 6.5105]}, "type": "Feature", "properties": {"close_time": 1346949000, "radius": 200, "name": "A01", "checkpoint_type": "goal", "open_time": 1346928300}}]}}')


class TestTrack(unittest.TestCase):

    def setUp(self):
        tid = track.TrackID()
        e1 = events.TrackCreated(tid,
                                 dict(track_type='competition_aftertask', race_task=th_fai_1_task))
        self.track = track.Track(tid, [e1])

    def tearDown(self):
        del self.track

    def test_init(self):
        self.assertIsInstance(self.track, track.Track)
        self.assertEqual(self.track.state['state'], 'not started')
        self.assertEqual(self.track.type.type, 'competition_aftertask')
        self.assertEqual(self.track.task.type, 'racetogoal')

    def test_parse_unfinished(self):
        self.track.append_data('1.2.609.609.igc')
        self.track.process_data()
        for ch in self.track.changes:
            print ch.name, datetime.fromtimestamp(ch.occured_on), ch.occured_on
        print len(self.track.points)
        self._check_events(self.track.changes, finished=False,
                           checkpoints_taken=3, amount=5)
        self._check_track_state(self.track._state, ended=True,
                                last_checkpoint=3, state='landed', last_distance=38837)

    def test_parse_finished(self):
        self.track.append_data('pwc13.task3.finished.79.igc')
        self.track.process_data()
        for ch in self.track.changes:
            print ch.name, ch.payload, datetime.fromtimestamp(ch
                                                              .occured_on), ch.occured_on
        print len(self.track.points)
        print 'distance:', self.track.points[-1]['distance']
        self._check_events(self.track.changes,
                           finish_time=1374243311,
                           finished=True, checkpoints_taken=6, amount=9)
        self._check_track_state(self.track._state,
                                finish_time=1374243311,
                                last_checkpoint=6,
                                ended=True)
        # 4 checkpoint taken at 16:45
        # es (5 checkpoint) taken at 17:20
        # track started at 12:40

    def _check_events(self, event_list, **kw):
        checkpoints_taken = 0
        self.assertEqual(len(event_list), kw.get('amount'))
        for ev in event_list:
            if ev.name == 'TrackFinishTimeReceived' and 'finish_time' in kw:
                self.assertEqual(ev.payload, kw['finish_time'])
            elif ev.name == 'TrackFinished' and 'finished' not in kw:
                self.fail("Track has been finished.")
            elif ev.name == 'TrackCheckpointTaken':
                checkpoints_taken += 1
        if 'checkpoints_taken' in kw:
            self.assertEqual(kw['checkpoints_taken'], checkpoints_taken)

    def _check_track_state(self, tstate, **kw):
        '''

        @param tstate:
        @type tstate: L{gorynych.processor.domain.track.TrackState}
        '''
        self.assertEqual(tstate.last_checkpoint, kw.get('last_checkpoint', 0))
        self.assertEqual(tstate.ended, kw.get('ended'))
        self.assertEqual(tstate.finish_time, kw.get('finish_time'))
        self.assertEqual(tstate.last_distance, kw.get('last_distance', 0))
        self.assertEqual(tstate.started, kw.get('started', True))
        self.assertEqual(tstate.state, kw.get('state', 'finished'))

    def test_parse_1d_error(self):
        self.track.append_data('cond.1d.3243.17.igc')
        self.track.process_data()
        for ch in self.track.changes:
            print ch.name, datetime.fromtimestamp(ch.occured_on)
        print len(self.track.points)

    def test_12thfai_littame(self):
        from gorynych.processor.infrastructure.persistence import find_snapshots
        self.track.append_data('0033.igc')
        self.track.process_data()
        for ch in self.track.changes:
            print ch.name, datetime.fromtimestamp(ch.occured_on)
        print len(self.track.points)
        self._check_track_state(self.track._state, ended=True,
                                state='finished', last_checkpoint=6, finish_time=1346939844)
        print find_snapshots(self.track)


class RaceTestCase(unittest.TestCase):
    """
    Common TestCase class for all the racetypes.
    """
    def _check_eventlist(self, evlist):
        for ev in evlist:
            self.assertIsInstance(ev, DomainEvent)
            self.assertEqual(getattr(ev, 'aggregate_type'), 'track')
            self.assertEqual(getattr(ev, 'aggregate_id'), self.track_id)

    def _check_taken_checkpoints(self, evlist):
        for i, ev in enumerate(evlist, start=1):
            self.assertEqual((i, 0), getattr(ev, 'payload'))
            self.assertEqual(getattr(ev, 'occured_on'),
                             self.complete_track[i]['timestamp'])

    def assertTrackIsComplete(self, evlist):
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
        for chp in self.test_race['checkpoints']['features']:
            if chp['properties']['checkpoint_type'] == 'ss':
                chp['properties']['radius'] = 200
        self.complete_track = make_pilot_points(self.test_race)
        self.rt = self.factory.create('online', self.test_race)
        self.track_id = track.TrackID()
        self.ts = track.TrackState(self.track_id, [])

    def test_init(self):
        self.assertIsInstance(self.rt, RaceToGoal)
        self.assertEqual(self.rt.type, 'racetogoal')
        self.assertTupleEqual((self.rt.start_time, self.rt.end_time), (1374223800,
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
        pts, evlist = self.rt.process(self.complete_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertTrackIsComplete(evlist)

    def test_one_checkpoint_missing(self):
        malformed_track = np.delete(self.complete_track, 3)
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
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
        # the same result as one missing checkpoints
        self._check_eventlist(evlist)
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
        self._check_eventlist(evlist)
        self.assertEqual(evlist, [])

    def test_takeoff_missing(self):
        malformed_track = self.complete_track[1:]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertTrackIsComplete(evlist)

    def test_goal_missing(self):
        malformed_track = self.complete_track[:-1]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
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


class TestSpeedrun(RaceTestCase):

    def setUp(self):
        self.factory = RaceTypesFactory()
        self.test_race = test_race.copy()
        self.test_race['race_type'] = 'speedrun'
        for chp in self.test_race['checkpoints']['features']:
            if chp['properties']['checkpoint_type'] == 'ss':
                chp['properties']['radius'] = 200
        self.complete_track = make_pilot_points(self.test_race)
        self.rt = self.factory.create('online', self.test_race)
        self.track_id = track.TrackID()
        self.ts = track.TrackState(self.track_id, [])

    def test_init(self):
        self.assertEqual(self.rt.type, 'speedrun')
        self.assertTupleEqual((self.rt.start_time, self.rt.end_time), (1374223800,
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
        pts, evlist = self.rt.process(self.complete_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertTrackIsComplete(evlist)

    def test_one_checkpoint_missing(self):
        malformed_track = np.delete(self.complete_track, 3)
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
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
        # the same result as one missing checkpoints
        self._check_eventlist(evlist)
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
        self._check_eventlist(evlist)
        self.assertEqual(evlist, [])

    def test_takeoff_missing(self):
        malformed_track = self.complete_track[1:]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertTrackIsComplete(evlist)

    def test_goal_missing(self):
        malformed_track = self.complete_track[:-1]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
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


class TestOpendistance(RaceTestCase):

    def setUp(self):
        self.factory = RaceTypesFactory()
        self.test_race = test_race.copy()
        self.test_race['race_type'] = 'opendistance'
        for chp in self.test_race['checkpoints']['features']:
            if chp['properties']['checkpoint_type'] == 'ss':
                chp['properties']['radius'] = 200
        self.complete_track = make_pilot_points(self.test_race)
        self.rt = self.factory.create('online', self.test_race)
        self.track_id = track.TrackID()
        self.ts = track.TrackState(self.track_id, [])

    def test_init(self):
        self.assertEqual(self.rt.type, 'opendistance')
        self.assertTupleEqual((self.rt.start_time, self.rt.end_time), (1374223800,
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
        pts, evlist = self.rt.process(self.complete_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(len(evlist), 6)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 6)
        self._check_taken_checkpoints(chp_taken)

    def test_one_checkpoint_missing(self):
        malformed_track = np.delete(self.complete_track, 3)
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(len(evlist), 2)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

    def test_two_checkpoints_missing(self):
        malformed_track = np.delete(self.complete_track, [3, 5])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(len(evlist), 2)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)

    def test_start_missing(self):
        malformed_track = np.delete(self.complete_track, [1, 2])
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(evlist, [])

    def test_takeoff_missing(self):
        malformed_track = self.complete_track[1:]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(len(evlist), 6)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 6)
        self._check_taken_checkpoints(chp_taken)

    def test_goal_missing(self):
        malformed_track = self.complete_track[:-1]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(len(evlist), 5)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 5)
        self._check_taken_checkpoints(chp_taken)

    def test_unfinished_task(self):
        malformed_track = self.complete_track[:3]
        pts, evlist = self.rt.process(malformed_track, self.ts, self.track_id)
        self._check_eventlist(evlist)
        self.assertEqual(len(evlist), 2)
        chp_taken = [ev for ev in evlist if
                     isinstance(ev, events.TrackCheckpointTaken)]
        self.assertEqual(len(chp_taken), 2)
        self._check_taken_checkpoints(chp_taken)