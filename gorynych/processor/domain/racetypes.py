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
    def __init__(self, chp, opt_point, error_margin):
        self.checkpoint = chp
        self.distance = 0
        self.error_margin = error_margin
        assert len(opt_point) == 2, "Optimum point parameter is wrong."
        assert isinstance(opt_point, tuple), "Need tuple as a point."
        self.opt_lat, self.opt_lon = opt_point

    def is_taken_by(self, lat, lon):
        dist_to_center = services.point_dist_calculator(
            lat, lon, self.checkpoint.lat, self.checkpoint.lon)
        return dist_to_center < (
            self.checkpoint.radius + self.error_margin)

    def dist_to_point(self, lat, lon):
        return services.point_dist_calculator(
            lat, lon, self.opt_lat, self.opt_lon)


class RaceTypesFactory(object):
    races = dict(racetogoal=RaceToGoal)
    error_margin = dict(online={'es':10, 'goal':10, 'default':1000},
                competition_aftertask={'es':10, 'goal':10, 'default':50})

    def create(self, rtype, rtask):
        '''
        @param rtask: dictionary with race task.
        @param rtype: string with task type: 'online',
        'competition_aftertask'.
        '''
        assert isinstance(rtask, dict), "Race task must be dict."
        race = self.races.get(rtask.get('race_type', 'racetogoal'),
            RaceToGoal)
        checkpoints = checkpoint_collection_from_geojson(rtask['checkpoints'])
        points, dist = services.JavaScriptShortWay().calculate(checkpoints)
        race_checkpoints = []
        for i, ch in enumerate(checkpoints):
            if ch.geometry.geom_type == 'Point':
                error_margin = self.error_margin[rtype].get(ch.type,
                    'default')
                cp = CylinderCheckpointAdapter(ch, points[i], error_margin)
                race_checkpoints.append(cp)
        race_checkpoints = getattr(self, '_distances_for_' + rtype)(
            race_checkpoints)
        return race(rtask, race_checkpoints)

    def _distances_for_racetogoal(self, race_checkpoints):
        '''

        @param race_checkpoints:
        @type race_checkpoints: list
        @return:
        @rtype:
        '''
        race_checkpoints.reverse()
        for idx, p in enumerate(race_checkpoints[1:]):
            dist_from_prev = p.dist_to_point(
                race_checkpoints[idx].opt_lat, race_checkpoints[idx].opt_lon)
            p.distance = race_checkpoints[idx].distance + dist_from_prev
        race_checkpoints.reverse()
        return race_checkpoints


