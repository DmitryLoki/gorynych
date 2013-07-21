# coding=utf-8
'''
Track aggregate.
'''

__author__ = 'Boris Tsema'
import uuid

import numpy as np

from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.info.domain.ids import namespace_uuid_validator
from gorynych.processor.domain import services
from gorynych.processor.domain.racetypes import RaceTypesFactory


DTYPE = [('id', 'i4'), ('timestamp', 'i4'), ('lat', 'f4'),
    ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
    ('distance', 'i4')]

EARTH_RADIUS = 6371000

def track_types(ttype):
    types = dict(competition_aftertask=services.FileParserAdapter(DTYPE),
        online=services.OnlineTrashAdapter(DTYPE))
    return types.get(ttype)


def race_tasks(rtask):
    assert isinstance(rtask, dict), "Race task must be dict."
    tasks = dict(racetogoal=RaceToGoal)
    res = tasks.get(rtask['race_type'])
    if res:
        return res(rtask)


class TrackID(DomainIdentifier):
    '''
    trck-749e0d12574a4d4594e72488461574d0'
    namespace-uuid4.hex
    '''
    def __init__(self):
        _uid = uuid.uuid4().hex
        self._id = '-'.join(('trck', _uid))

    def _string_is_valid_id(self, string):
        return namespace_uuid_validator(string, 'trck')


class TrackState(ValueObject):
    '''
    Hold track state. Memento.
    '''
    states = ['not started', 'started', 'finished', 'landed']
    def __init__(self, id, event_list):
        self.id = id
        # Time when track speed become more then threshold.
        self.become_fast = None
        self.become_slow = None
        self.track_type = None
        self.race_task = None
        self.last_checkpoint = 0
        self.state = 'not started'
        self.statechanged_at = None
        self.started = False
        self.in_air = False
        self.start_time = None
        # Buffer for points.
        self._buffer = np.empty(0, dtype=DTYPE)
        # Time at which track has been ended.
        self.end_time = None
        self.ended = False
        self.finish_time = None
        self.last_distance = 0
        for ev in event_list:
            self.mutate(ev)

    def mutate(self, ev):
        '''
        Mutate state according to event. Analog of apply method in AggregateRoot.
        '''
        evname = ev.__class__.__name__
        if hasattr(self, 'apply_' + evname):
            getattr(self, 'apply_' + evname)(ev)

    def apply_TrackCreated(self, ev):
        self.track_type = ev.payload['track_type']
        self.race_task = ev.payload['race_task']

    def apply_TrackCheckpointTaken(self, ev):
        n = ev.payload[0]
        if self.last_checkpoint < n:
            self.last_checkpoint = n

    def apply_TrackStarted(self, ev):
        if not self.started:
            self.state = 'started'
            self.start_time = ev.occured_on
            self.statechanged_at = ev.occured_on
            self.started = True

    def apply_TrackEnded(self, ev):
        if not self.state == 'finished':
            self.state = ev.payload['state']
            self.statechanged_at = ev.occured_on
        self.ended = True
        self.end_time = ev.occured_on
        self.last_distance = ev.payload.get('distance')

    def apply_TrackFinished(self, ev):
        if not self.state == 'finished':
            self.state = 'finished'
            self.statechanged_at = ev.occured_on

    def apply_TrackFinishTimeReceived(self, ev):
        self.finish_time = ev.payload

    def apply_TrackInAir(self, ev):
        self.in_air = True

    def apply_TrackSlowedDown(self, ev):
        self.become_fast, self.become_slow = None, ev.occured_on

    def apply_TrackSpeedExceeded(self, ev):
        self.become_slow, self.become_fast = None, ev.occured_on

    def apply_TrackLanded(self, ev):
        self.in_air = False
        if not self.state == 'finished':
            self.state = 'landed'
            self.last_distance = int(ev.payload)
            self.statechanged_at = ev.occured_on

    def get_state(self):
        result = dict()
        result['state'] = self.state
        result['statechanged_at'] = self.statechanged_at
        return result


class Track(AggregateRoot):

    dtype = DTYPE

    def __init__(self, id, events=None):
        super(Track, self).__init__()
        self.id = id
        self._id = None
        self._state = TrackState(id, events)
        self._task = None
        self._type = None
        self.changes = []
        # New processed points.
        self.points = np.empty(0, dtype=self.dtype)
        # Buffer for appended to track data.
        self.buffer = np.empty(0, dtype=self.dtype)
        # Processed points holded for future processing.
        self.processed = np.empty(0, dtype=self.dtype)
        # track data can be introduced as
        # np.hstack((processed, points, buffer))

    def apply(self, ev):
        if isinstance(ev, list):
            for e in ev:
                self._state.mutate(e)
                self.changes.append(e)
        else:
            self._state.mutate(ev)
            self.changes.append(ev)

    def append_data(self, data):
        self.buffer = services.create_uniq_hstack(
                                    self.buffer, self.type.read(data))
        self.buffer = self.buffer[
            np.where(self.buffer['timestamp'] >=self.task.start_time)]

    def process_data(self):
        points, evs = self.type.process(self.buffer, self)
        self.apply(evs)
        if points is None:
            return
        self.buffer = np.empty(0, dtype=self.dtype)
        #evs = services.ParagliderSkyEarth(self._state).state_work(points)
        #self.apply(evs)
        # Task process points and emit new events if occur.
        points, ev_list = self.task.process(points, self._state, self.id)
        self.apply(ev_list)
        self.points = services.create_uniq_hstack(self.points, points)
        # Look for state after processing and do all correctness.
        evlist = self.type.correct(self)
        self.apply(evlist)
        self.changes = services.clean_events(self.changes)

    @property
    def state(self):
        return self._state.get_state()

    @property
    def task(self):
        if not self._task:
            self._task = RaceTypesFactory().create(
                self._state.track_type, self._state.race_task)
        return self._task

    @property
    def type(self):
        if not self._type:
            self._type = track_types(self._state.track_type)
        return self._type

    def reset(self):
        self.changes=[]
        self.processed = services.create_uniq_hstack(self.processed,
            self.points)[-100:]
        self.points = np.empty(0, dtype=self.dtype)

