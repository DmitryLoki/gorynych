import numpy as np
from gorynych.common.domain import events
from gorynych.common.domain.types import checkpoint_collection_from_geojson
from gorynych.processor.domain.track import DTYPE
from gorynych.processor.domain import services


class RaceToGoal(object):
    '''
    Incapsulate race parameters calculation.
    '''
    type = 'racetogoal'
    wp_error = 300
    def __init__(self, task):
        chlist = task['checkpoints']
        self.checkpoints = checkpoint_collection_from_geojson(chlist)
        self.start_time = int(task['start_time'])
        self.end_time = int(task['end_time'])
        self.calculate_path()

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
        assert isinstance(points, np.ndarray), "Got %s instead of array" % \
                                               type(points)
        assert points.dtype == DTYPE
        eventlist = []
        lastchp = taskstate.last_checkpoint
        if lastchp < len(self.checkpoints) - 1:
            nextchp = self.checkpoints[lastchp + 1]
        else:
            # Last point taken but we still have data.
            if taskstate.last_distance:
                for p in points:
                    p['distance'] = taskstate.last_distance
                return points, []
            else:
                for p in points:
                    p['distance'] = 200
                return points, []
        if taskstate.state == 'landed':
            if taskstate.last_distance:
                for p in points:
                    p['distance'] = taskstate.last_distance
                return points, []
            else:
                for p in points:
                    p['distance'] = 200
                return points, []

        ended = taskstate.ended
        for idx, p in np.ndenumerate(points):
            dist = nextchp.distance_to((p['lat'], p['lon']))
            if dist - nextchp.radius <= self.wp_error and not ended:
                eventlist.append(
                    events.TrackCheckpointTaken(_id, (lastchp+1, int(dist)),
                                                    occured_on=p['timestamp']))
                if nextchp.type == 'es':
                    eventlist.append(events.TrackFinishTimeReceived(_id,
                        payload=p['timestamp']))
                    self.wp_error = 20
                if nextchp.type == 'goal':
                    eventlist.append(events.TrackFinished(_id,
                        occured_on=taskstate.finish_time))
                    ended = True
                    self.wp_error = 20
                if nextchp.type == 'ss':
                    eventlist.append(events.TrackStarted(_id,
                        occured_on=p['timestamp']))
                if lastchp + 1 < len(self.checkpoints) - 1:
                    nextchp = self.checkpoints[lastchp + 2]
                    lastchp += 1
            p['distance'] = int(dist + nextchp.distance)

        return points, eventlist


class CylinderCheckpointAdapter(object):
    def __init__(self, chp):
        self.checkpoint = chp
        # Distance from(to) this checkpoint.
        self._distance = 0
        self._dist_to_opt_point = 0
        self._dist_to_center = 0
        self.error_margin = 0

    def process(self, lat, lon):
        opt_lat = self.checkpoint.aPoint.lat
        opt_lon = self.checkpoint.aPoint.lon
        dist_to_opt_point = services.point_dist_calculator(
            lat, lon, opt_lat, opt_lon)
        self._dist_to_opt_point = dist_to_opt_point
        self._dist_to_center = services.point_dist_calculator(
            lat, lon, self.checkpoint.lat, self.checkpoint.lon)

    @property
    def taken(self):
        return self._dist_to_center < (
            self.checkpoint.radius + self.error_margin)

    @property
    def distance(self):
        return self._dist_to_opt_point

