'''
Track aggregate.
'''
__author__ = 'Boris Tsema'

import numpy as np

from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.processor.domain import services
from gorynych.processor import events
from gorynych.common.domain.types import checkpoint_collection_from_geojson

DTYPE = [('id', 'i8'), ('timestamp', 'i4'), ('lat', 'f4'),
    ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
    ('distance', 'i4')]

EARTH_RADIUS = 6371000

def track_types(ttype):
    types = dict(competition_aftertask=services.FileParserAdapter(DTYPE))
    return types.get(ttype)


def race_tasks(rtask):
    tasks = dict(racetogoal=RaceToGoal)
    res = tasks.get(rtask['type'])
    if res:
        return res(rtask)


class TrackID(DomainIdentifier): pass


class TrackState(ValueObject):
    '''
    Hold track state. Memento.
    '''
    def __init__(self, events):
        # Buffer for points. It has fixed length or fixed time amount.
        self.pbuffer = np.empty(0, dtype=DTYPE)
        for ev in events:
            self.mutate(ev)
        # necessary fields
        self.track_type = None
        self.race_task = None
        self.last_checkpoint = 0
        # Time at which track has been ended.
        self.end_time = 0
        self.ended = False
        self.finish_time = None

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

    def apply_TrackEnded(self, ev):
        if self.state == 'finished':
            return
        self.state = ev.payload['state']
        self.statechanged_at = ev.occured_on

    def apply_PointsAddedToTrack(self, ev):
        pass

    def apply_TrackFinished(self, ev):
        self.state = 'finished'

    def apply_TrackStarted(self, ev):
        pass

    def apply_TrackFinishTimeReceived(self, ev):
        self.finish_time = ev.payload

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

    def _process(self, data):
        # Now TrackType correct points and calculate smth if needed.
        points, evs = self.type.process(self._state, data,
            self.task.start_time, self.task.end_time)
        for ev in evs:
            self.apply(ev)
        # Task process points and emit new events if occur.
        points, ev_list = self.task.process(points, self._state, self.id)
        for ev in ev_list:
            self.apply(ev)
        # Don't sure about this.
        self.processed_points, self.points = points[:-1], points[-1]
        ev = events.TrackDataReceived(self.id, self.processed_points)
        ev.occured_on = self.processed_points['timestamp'][-1]
        self.apply(ev)
        # Look for state after processing and do all correctness.
        evlist = self.type.correct(self._state)
        for ev in evlist:
            self.apply(ev)

    def _accumulate_points(self, data):
        '''
        Collect enough amount of points, order it and send to processing.
        '''
        # TODO: handle receiving of disordered data.
        pbuffer = self._state.pbuffer
        if not self.points:
            # First data received.
            # Process data and write something in self.points. Also emit events
            # to fill self._state.pbuffer.
            self._process(data)
            return
        if data['timestamp'][-1] - self.points['timestamp'][0] > self.flush_time:
            # Got enough points for calculation.
            self._process(data)
        else:
            # Don't hav enough points. Add it to buffer,
            # but don't forget to check it after flush_time.
            self.points = self._update_buffer(data)

    def check_buffer(self):
        '''
        Called by application service. Check for stale self.points and
        perform calculation if time is come.
        '''
        raise NotImplementedError()

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

    def _update_buffer(self, data):
        raise NotImplementedError()


class RaceToGoal:
    '''
    Incapsulate race parameters calculation.
    '''
    type = 'racetogoal'
    wp_error = 30
    def __init__(self, task):
        chlist = task['checkpoints']['features']
        self.checkpoints = checkpoint_collection_from_geojson(chlist)
        self.start_time, self.end_time = task['start_time'], task['end_time']

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
                    events.TrackCheckpointTaken(_id, (lastchp+1, dist),
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

