'''
Track aggregate.
'''
from collections import deque

__author__ = 'Boris Tsema'

import numpy as np

from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.common.infrastructure import persistence as pe
from gorynych.processor.domain import services
from gorynych.processor import events

DTYPE = [('id', 'i8'), ('timestamp', 'i4'), ('lat', 'f4'),
    ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
    ('distance', 'i4')]


def track_types(ttype):
    types = {'competition aftertask': FileParserAdapter(DTYPE)}
    return types.get(ttype)


class TrackID(DomainIdentifier): pass


class TrackState(ValueObject):
    '''
    Hold track state. Memento.
    '''
    def __init__(self, events):
        # Buffer for points.
        self.points = np.empty(0, dtype=DTYPE)
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
    dtype = DTYPE

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
        # Here TrackType read data and return it in good common format.
        data = self.type.read(data)
        self._accumulate_points(data)

    def _accumulate_points(self, data):
        if self.points and (data['timestamp'][-1] -
                        self.points['timestamp'][0]) > self.flush_time:
            # Got enough points for calculation.
            # Now TrackType correct points and calculate smth if needed.
            points = self.type.process(self._state, data, self.task.start_time,
                                                            self.task.end_time)
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
            self._type = track_types(self._state.track_type)
        return self._type


class FileParserAdapter(object):
    def __init__(self, dtype):
        self.dtype = dtype

    def read(self, data):
        try:
            parsed_track = services.choose_offline_parser(data)(self.dtype
                                                                ).parse(data)
        except Exception as e:
            raise Exception("Error while parsing file: %r " % e)
        return parsed_track

    def process(self, data, trackstate, stime, etime):
        corrector = services.OfflineCorrectorService()
        try:
            track = corrector.correct_track(data, stime, etime)
        except Exception as e:
            raise Exception("Error while correcting track: %r " % e)
        track['v_speed'] = services.vspeed_calculator(track['alt'],
            track['timestamp'])
        track['g_speed'] = services.gspeed_calculator(track['lat'],
            track['lon'],
            track['timestamp'])
        return track


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


