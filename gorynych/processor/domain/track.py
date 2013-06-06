'''
Track aggregate.
'''
__author__ = 'Boris Tsema'

import numpy as np
from zope.interface import Interface

from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.common.domain import events
from gorynych.common.domain.types import checkpoint_collection_from_geojson
from gorynych.processor.domain import services

DTYPE = [('id', 'i4'), ('timestamp', 'i4'), ('lat', 'f4'),
    ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
    ('distance', 'i4')]

EARTH_RADIUS = 6371000

def track_types(ttype):
    types = dict(competition_aftertask=services.FileParserAdapter(DTYPE))
    return types.get(ttype)


def race_tasks(rtask):
    assert isinstance(rtask, dict), "Race task must be dict."
    tasks = dict(racetogoal=RaceToGoal)
    res = tasks.get(rtask['race_type'])
    if res:
        return res(rtask)


class TrackID(DomainIdentifier): pass


class TrackState(ValueObject):
    '''
    Hold track state. Memento.
    '''
    states = ['not started', 'started', 'finished', 'landed']
    def __init__(self, events):
        self.track_type = None
        self.race_task = None
        self.last_checkpoint = 0
        self.state = 'not started'
        self.statechanged_at = None
        self.started = False
        self.start_time = None
        self.pbuffer = np.empty(0, dtype=DTYPE)
        # Time at which track has been ended.
        self.end_time = None
        self.ended = False
        self.finish_time = None
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

    def apply_PointsAddedToTrack(self, ev):
        self.pbuffer = ev.payload

    def apply_TrackEnded(self, ev):
        if not self.state == 'finished':
            self.state = ev.payload['state']
            self.statechanged_at = ev.occured_on
        self.ended = True
        self.end_time = ev.occured_on

    def apply_TrackFinished(self, ev):
        if not self.state == 'finished':
            self.state = 'finished'
            self.statechanged_at = ev.occured_on

    def apply_TrackFinishTimeReceived(self, ev):
        self.finish_time = ev.payload

    def get_state(self):
        result = dict()
        result['points'] = self.pbuffer
        result['state'] = self.state
        result['statechanged_at'] = self.statechanged_at
        return result


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
        # Now TrackType correct points and calculate smth if needed.
        points, evs = self.type.process(data,
            self.task.start_time, self.task.end_time)
        for ev in evs:
            self.apply(ev)
        # Task process points and emit new events if occur.
        points, ev_list = self.task.process(points, self._state, self.id)
        for ev in ev_list:
            self.apply(ev)
        ev = events.PointsAddedToTrack(self.id, points)
        ev.occured_on = points['timestamp'][0]
        self.apply(ev)
        # Look for state after processing and do all correctness.
        evlist = self.type.correct(self._state, self.id)
        for ev in evlist:
            self.apply(ev)

    @property
    def state(self):
        return self._state.get_state()

    @property
    def task(self):
        if not self._task:
            self._task = race_tasks(self._state.race_task)
        return self._task

    @property
    def type(self):
        if not self._type:
            self._type = track_types(self._state.track_type)
        return self._type


class RaceToGoal(object):
    '''
    Incapsulate race parameters calculation.
    '''
    type = 'racetogoal'
    wp_error = 30
    def __init__(self, task):
        chlist = task['checkpoints']
        self.checkpoints = checkpoint_collection_from_geojson(chlist)
        self.start_time = int(task['start_time'])
        self.end_time = int(task['end_time'])

    def calculate_path(self):
        '''
        For a list of checkpoints calculate distance from concrete
        checkpoint to the goal.
        @return:
        @rtype:
        '''
        self.checkpoints.reverse()
        self.checkpoints[0].distance = 0
        for idx, p in enumerate(self.checkpoints[1:]):
            p.distance = int(p.distance_to(self.checkpoints[idx]))
            p.distance += self.checkpoints[idx].distance
        self.checkpoints.reverse()

    def process(self, points, taskstate, _id):
        '''
        Process points and emit events if needed.
        @param points: array with points for some seconds (minute usually).
        @type points: C{np.array}
        @param taskstate: read-only object implementing track state.
        @type taskstate: L{TrackState}
        @return: (points, event list)
        @rtype: (np.array, list)
        '''
        eventlist = []
        lastchp = taskstate.last_checkpoint
        if lastchp < len(self.checkpoints) - 1:
            nextchp = self.checkpoints[lastchp + 1]
        else:
            # Impossible situation because track should be ended before.
            for p in points:
                p['distance'] = taskstate.pbuffer[-1]['distance']
            return points
        ended = taskstate.ended
        for p in points:
            dist = nextchp.distance_to((p['lat'], p['lon']))
            if dist <= self.wp_error and not ended:
                eventlist.append(
                    events.TrackCheckpointTaken(_id, (lastchp+1, int(dist)),
                                                    occured_on=p['timestamp']))
                if nextchp.type == 'es':
                    eventlist.append(events.TrackFinishTimeReceived(_id,
                        payload=p['timestamp']))
                if nextchp.type == 'goal':
                    eventlist.append(events.TrackFinished(_id,
                        occured_on=taskstate.finish_time))
                    ended = True
                if nextchp.type == 'ss':
                    eventlist.append(events.TrackStarted(_id,
                        occured_on=p['timestamp']))
                if lastchp + 1 < len(self.checkpoints) - 1:
                    nextchp = self.checkpoints[lastchp + 2]
            p['distance'] = int(dist + nextchp.distance)

        return points, eventlist


class ITrackRepository(Interface):
    def save(track):
        '''
        Save track.
        @param track:
        @type track:
        @return:
        @rtype:
        '''