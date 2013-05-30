'''
Track aggregate.
'''
from collections import deque

__author__ = 'Boris Tsema'

import numpy.ma as ma
import numpy as np

from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.common.infrastructure import persistence as pe
from gorynych.processor.domain import services
from gorynych.processor import events


class TrackID(DomainIdentifier): pass


class TrackState(ValueObject):
    '''
    Hold track state. Memento.
    '''
    def __init__(self, events):
        # Buffer for points.
        self.points = np.empty(0, dtype=self.dtype)
        for ev in events:
            self.mutate(ev)

    def mutate(self, ev):
        '''
        Mutate state according to event. Analog of apply method in AggregateRoot.
        @param ev:
        @type ev:
        @return:
        @rtype:
        '''
        evname = ev.__class__.__name__
        if hasattr(self, 'apply_' + evname):
            getattr(self, 'apply_' + evname)(ev)

    def apply_TrackCreated(self, ev):
        pass

    def apply_TrackDataReceived(self, ev):
        '''
        Process received data and emit event if occur.
        @param ev: TrackDataReceived event
        @type ev: implementor of L{IEvent}
        @return:
        @rtype: C{Deferred}
        '''

        self.state, new_event = self.type.process(ev.payload, self.state)
        if new_event:
            # TODO: implement list handling in EventStore.persist().
            return pe.event_store().persist(new_event)

    def apply_TrackEnded(self, ev):
        pass

    def get_state(self):
        pass


class Track(AggregateRoot):

    flush_time = 60
    dtype = [('id', 'i8'), ('timestamp', 'i4'), ('lat', 'f4'),
        ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
        ('distance', 'i4')]

    def __init__(self, id, events=None):
        self.id = id
        self._state = TrackState(events)
        self._task = None
        self._type = None
        self.changes = []
        # Buffer for points.
        self.points = np.empty(0, dtype=self.dtype)

    def apply(self, ev):
        self._state.mutate(ev)
        self.changes.append(ev)

    def process_data(self, data):
        # Here type read data and return it in good common format.
        data = self.type.read(data)
        self._accumulate_points(data)

    def _accumulate_points(self, data):
        if self.points and (data['timestamp'][-1] -
                        self.points['timestamp'][0]) > self.flush_time:
            # Got enough points for calculation.
            # Now TrackType correct points and calculate smth if needed.
            points, evs = self.type.process(self._state, data)
            for ev in evs:
                # Here I'm waiting for Unordered point events and so on.
                # Only online tracks can emit events here, I tnihk.
                self.apply(ev)
            # Task process points and emit new events if occur.
            points, ev_list = self.task.process(points, self._state)
            for ev in ev_list:
                self.apply(ev)
            # Don't sure about this.
            self.processed_points, self.points = points[:-1], points[-1]
            ev = events.TrackDataReceived(self.id, self.processed_points)
            ev.occured_on = self.processed_points['timestamp'][-1]
            self.apply(ev)
        else:
            self.points = np.concatenate(self.points, data)

    @property
    def state(self):
        return self._state.get_state()

    @property
    def task(self):
        if not self._task:
            self._task = RaceTask.create(self._state.race_task)
        return self._task

    @property
    def type(self):
        if not self._type:
            self._type = TrackType.create(self._state.track_type)
        return self._task




class RaceTask:
    '''
    Incapsulate race parameters calculation.
    '''
    @classmethod
    def create(cls, value):
        '''
        Fabric method.
        @param cls:
        @type cls:
        @param value:
        @type value:
        @return:
        @rtype:
        '''
        return cls(value)


class TrackType:
    @classmethod
    def create(cls, value):
        '''
        Fabric method.
        @param cls:
        @type cls:
        @param value:
        @type value:
        @return:
        @rtype:
        '''
        return cls(value)


class OfflineCorrectorMixin:
    '''
    Cut track and correct it.
    '''
    # Maximum gap in track after which it accounted as finished (in seconds).
    maxtimediff = 300

    def _clean_timestamps(self, track):
        '''
        Cut track in time and make array with timestamps monotonic.
        @param track:
        @type track:
        @return:
        @rtype:
        '''
        data = ma.masked_inside(track, self.tracktask.start_time,
            self.tracktask.end_time)
        track = track.compress(data.mask)
        # Eliminate repetitive points.
        times, indices = np.unique(track['timestamp'], return_index=True)
        track = track[indices]
        # Here we still can has points reversed in time. Fix it.
        tdifs = np.ediff1d(data['timestamp'], to_begin=1)
        # At first let's find end of track by timeout, if any.
        track_end_idxs = np.where(tdifs > self.maxtimediff)[0]
        if track_end_idxs:
            track_end_idxs = track_end_idxs[0]
            track = track[:track_end_idxs]
            tdifs = tdifs[:track_end_idxs]

        # Eliminate reverse points.
        data = ma.masked_greater(tdifs, 0)
        track = track.compress(data.mask)
        return track

    def correct_track(self, track):
        '''
        Receive raw parsed data, cut it and looks for bad times.
        @param track: array with dtype defined in L{CompetitionTrack}
        @type track: C{numpy.array}
        @return track without dublicated or reversed points in timescale.
        @rtype: C{numpy.array}
        '''
        # Eliminate points outside task time.
        track = self._clean_timestamps(track)
        return services.ParaglidingTrackCorrector().correct_data(track)


class CompetitionTrack:
    # np.array dtype for data
    dtype = [('id', 'i8'), ('timestamp', 'i4'), ('lat', 'f4'),
        ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
        ('distance', 'i4')]

    def __init__(self, tracktask):
        self.tracktask = tracktask
        # TODO: implement good buffer for track points or use self.data?
        self.trackbuffer = deque(50)
        self.data = np.empty(1, self.dtype)

    def process_task_data(self, data, trackstate):
        returned_events = []
        a = len(trackstate)
        result, trackstate = self.tracktask.process(data, trackstate)
        for item in trackstate[a - 1:]:
            returned_events.append(self.analyze_competition_event(item))
        return trackstate, returned_events

    def analyze_competition_event(self, item):
        pass


def runs_of_ones_array(bits):
    '''
    Calculate start and end indexes of subarray of ones in array.
    @param bits:
    @type bits:
    @return:
    @rtype:
    '''
    # make sure all runs of ones are well-bounded
    bounded = np.hstack(([0], bits, [0]))
    # get 1 at run starts and -1 at run ends
    difs = np.diff(bounded)
    run_starts, = np.where(difs > 0)
    run_ends, = np.where(difs < 0)
    return run_starts, run_ends


class OnlineCorrectorMixin:
    '''
    Here I check that all data has been taken in correct order. Only reorder
     work will be here.
    '''

    def check_data(self, data):
        pass


class ParagliderTrackMixin:
    threshold_speed = 10
    # Threshold value for 'not started'-'flying' change in km/h.
    sf_speed = 20
    # Threshold value for 'flying'-'not started' change in km/h.
    fs_speed = 10
    # Time interval in which is allowed for pilot to be slow, seconds.
    slow_interval = 60
    alt_interval = 5

    __state = 'not started'

    def sky_earth_definer(self):
        overspeed_idxs = np.where(self.data['g_speed'] > self.threshold_speed)
        rs, re = runs_of_ones_array(overspeed_idxs)
        for i in xrange(len(rs)):
            if self.data['timestamp'][re[i]] - self.data['timestamp'][re[i]]\
                    > self.slow_interval:
                # TODO: wrap it in event.
                self.__state = 'flying'
                ts = self.data['timestamp'][re[i]]
                break

        lowspeed_idxs = np.where(self.data['g_speed'] < self.threshold_speed)
        rls, rle = runs_of_ones_array(lowspeed_idxs)
        # TODO: do the same as above.

    def _state_work(self, kw):
        ''' Calculate pilot's state.'''
        if kw['hs'] > self.sf_speed and self.__state == 'not started':
            self.__state = 'flying'
        if self.__state == 'flying':
            if self._slow and (kw['ts'] -
                                   self._became_slow >= self.slow_interval):
                self.state = 'landed'
            elif self._slow and (kw['hs'] > self.fs_speed or
                                         abs(kw['alt'] - self._slow_alt) > self.alt_interval):
                self._slow = False
            elif (not self._slow) and kw['hs'] < self.fs_speed:
                self._slow = True
                self._slow_alt = kw['alt']
                self._became_slow = kw['ts']

        if (self.last_wp > self._task['p_amount'] - 1 and
                self.race.is_finished(self.state, (self.lat, self.lon))):
            self.state = 'finished'
            self.fin_time = self.ts


class CompetitionOnline(CompetitionTrack,
    OnlineCorrectorMixin,
    ParagliderTrackMixin):
    def process(self, data, trackstate):
        takeoff_time, landing_time = self.sky_earth_definer()
        data = self.check_data(data)
        # Some state work and event publishing.
        return self.process_task_data(data, trackstate)


class CompetitionAftertask(CompetitionTrack,
    OfflineCorrectorMixin,
    ParagliderTrackMixin):
    def process(self, trackfile, trackstate):
        try:
            parsed_track = services.choose_offline_parser(trackfile)(
                self.dtype
            ).parse(trackfile)
        except Exception as e:
            raise Exception("Error while parsing file: %r " % e)
        try:
            track = self.correct_track(parsed_track)
        except Exception as e:
            raise Exception("Error while correcting track: %r " % e)
        track['v_speed'] = services.vspeed_calculator(track['alt'],
            track['timestamp'])
        track['g_speed'] = services.gspeed_calculator(track['lat'],
            track['lon'],
            track['timestamp'])
        self.data = track
        takeoff_time, landing_time = self.sky_earth_definer()
        # TODO: persist domain events TrackStarted and TrackEnded.
        # Here I have correct track points from take off to landing.
        return self.process_task_data(track, trackstate)

