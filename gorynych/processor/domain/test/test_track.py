import simplejson as json
from datetime import datetime

from twisted.trial import unittest
from gorynych.processor.domain import track
from gorynych.common.domain import events


test_race = json.loads(
    '{"contest_title":"13th FAI World Paragliding Championship","country":"Bulgaria","place":"Sopot","timeoffset":"+0300","race_title":"Task 3","race_type":"racetogoal","start_time":"1374223800","end_time":"1374249600","bearing":"None","checkpoints":{"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [42.687497, 24.750131]}, "type": "Feature", "properties": {"close_time": 1374238200, "radius": 400, "name": "25S145", "checkpoint_type": "to", "open_time": 1374223800}}, {"geometry": {"type": "Point", "coordinates": [42.603923, 25.019128]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 21000, "name": "40L057", "checkpoint_type": "ss", "open_time": 1374226800}}, {"geometry": {"type": "Point", "coordinates": [42.603923, 25.019128]}, "type": "Feature", "properties": {"close_time": null, "radius": 4000, "name": "40L057", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.502614, 24.16646]}, "type": "Feature", "properties": {"close_time": null, "radius": 32000, "name": "04L055", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.504597, 25.026856]}, "type": "Feature", "properties": {"close_time": null, "radius": 5000, "name": "41P075", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [42.659186, 24.68335]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 2000, "name": "21L043", "checkpoint_type": "es", "open_time": 1374226800}}, {"geometry": {"type": "Point", "coordinates": [42.659186, 24.68335]}, "type": "Feature", "properties": {"close_time": 1374249600, "radius": 200, "name": "21L043", "checkpoint_type": "goal", "open_time": 1374226800}}]}}')

th_fai_1_task = json.loads(
    '{"contest_title":"12th  FAI European Paragliding Championship","country":"France","place":"Saint andre les alpes","timeoffset":"+0200","race_title":"Task 1 - 103 km","race_type":"racetogoal","start_time":"1346924700","end_time":"1346949000","bearing":"None","checkpoints":{"type": "FeatureCollection", "features": [{"geometry": {"type": "Point", "coordinates": [43.9785, 6.48]}, "type": "Feature", "properties": {"close_time": 1346930100, "radius": 1, "name": "D01", "checkpoint_type": "to", "open_time": 1346924700}}, {"geometry": {"type": "Point", "coordinates": [43.9388333333, 6.4078333333]}, "type": "Feature", "properties": {"close_time": 1346949000, "radius": 5000, "name": "B40", "checkpoint_type": "ss", "open_time": 1346928300}}, {"geometry": {"type": "Point", "coordinates": [44.4063333333, 6.2163333333]}, "type": "Feature", "properties": {"close_time": null, "radius": 20000, "name": "B13", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [43.7578333333, 6.6238333333]}, "type": "Feature", "properties": {"close_time": null, "radius": 20000, "name": "B15", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [43.9878333333, 6.3643333333]}, "type": "Feature", "properties": {"close_time": null, "radius": 1000, "name": "B42", "checkpoint_type": "ordinal", "open_time": null}}, {"geometry": {"type": "Point", "coordinates": [43.9658333333, 6.5578333333]}, "type": "Feature", "properties": {"close_time": 1346949000, "radius": 1000, "name": "B37", "checkpoint_type": "es", "open_time": 1346928300}}, {"geometry": {"type": "Point", "coordinates": [43.9586666667, 6.5105]}, "type": "Feature", "properties": {"close_time": 1346949000, "radius": 200, "name": "A01", "checkpoint_type": "goal", "open_time": 1346928300}}]}}')


class TestTrack(unittest.TestCase):

    def setUp(self):
        tid = track.TrackID()
        e1 = events.TrackCreated(tid,
                                 dict(track_type='competition_aftertask',
                                     race_task=test_race))
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
                           finish_time=1374243310,
                           finished=True, checkpoints_taken=6, amount=9)
        self._check_track_state(self.track._state,
                                finish_time=1374243310,
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
        from gorynych.processor.infrastructure.persistence import find_aftertasks_snapshots
        self.track.append_data('0033.igc')
        self.track.process_data()
        for ch in self.track.changes:
            print ch.name, datetime.fromtimestamp(ch.occured_on)
        print len(self.track.points)
        self._check_track_state(self.track._state, ended=True,
                                state='finished', last_checkpoint=6, finish_time=1346939844)
        print find_aftertasks_snapshots(self.track)
