import numpy as np
from gorynych.common.domain import events
from gorynych.common.domain.types import checkpoint_collection_from_geojson
from gorynych.processor.domain import services


class RaceToGoal(object):
    '''
    Incapsulate race parameters calculation.
    '''
    type = 'racetogoal'

    def __init__(self, task, checkpoints):
        self.checkpoints = checkpoints
        self.start_time = int(task['start_time'])
        self.end_time = int(task['end_time'])

    def process(self, points, taskstate, _id):
        '''
        Process points and emit events if needed.
        @param points: array with points for some seconds (minute usually).
        @type points: C{np.array}
        @param taskstate: read-only object implementing track state.
        @type taskstate: gorynych.processor.domain.track.TaskState
        @return: (points, event list)
        @rtype: (np.array, list)
        '''
        assert isinstance(points, np.ndarray), "Got %s instead of ndarray" % \
                                               type(points)
        eventlist = []
        lastchp = taskstate.last_checkpoint
        if lastchp < len(self.checkpoints) - 1:
            nextchp = self.checkpoints[lastchp + 1]
        else:
            # Last point has been taken but we still have data.
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

        calculation_ended = taskstate.ended
        for idx, p in np.ndenumerate(points):
            lat, lon = p['lat'], p['lon']
            if nextchp.is_taken_by(lat, lon) and not calculation_ended:
                eventlist.append(
                    events.TrackCheckpointTaken(
                        _id,
                        (lastchp+1, nextchp.dist_to_center),
                        occured_on=p['timestamp']))
                if nextchp.type == 'es':
                    eventlist.append(events.TrackFinishTimeReceived(_id,
                        payload=p['timestamp']))
                if nextchp.type == 'goal':
                    eventlist.append(events.TrackFinished(_id,
                        occured_on=taskstate.finish_time))
                    calculation_ended = True
                if nextchp.type == 'ss':
                    eventlist.append(events.TrackStarted(_id,
                        occured_on=p['timestamp']))
                if lastchp + 1 < len(self.checkpoints) - 1:
                    nextchp = self.checkpoints[lastchp + 2]
                    lastchp += 1
            p['distance'] = nextchp.dist_to_point(lat, lon) + nextchp.distance

        return points, eventlist


class CylinderCheckpointAdapter(object):
    def __init__(self, chp, opt_point, error_margin):
        '''
        @param chp:
        @type chp: gorynych.common.domain.types.Checkpoint.
        @param opt_point:
        @type opt_point:
        @param error_margin:
        @type error_margin:
        @return:
        @rtype:
        '''

        self.checkpoint = chp
        self.distance = 0
        self.error_margin = error_margin
        assert len(opt_point) == 2, "Optimum point parameter is wrong."
        assert isinstance(opt_point, tuple), "Need tuple as a point."
        self.opt_lat, self.opt_lon = opt_point

    def is_taken_by(self, lat, lon):
        '''
        Is point (lat, lon) inside the circle?
        @param lat:
        @type lat:
        @param lon:
        @type lon:
        @return:
        @rtype: boolean
        '''
        self.dist_to_center = services.point_dist_calculator(
            lat, lon, self.checkpoint.lat, self.checkpoint.lon)
        return self.dist_to_center < (
            self.checkpoint.radius + self.error_margin)

    def dist_to_point(self, lat, lon):
        '''
        Return distance in meters from point with coordinates lat,
        lon to circle optimum point.
        @param lat:
        @type lat: float
        @param lon:
        @type lon: float
        @return:
        @rtype: int
        '''
        return int(services.point_dist_calculator(
            lat, lon, self.opt_lat, self.opt_lon))

    @property
    def type(self):
        return self.checkpoint.type


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
                    self.error_margin[rtype]['default'])
                cp = CylinderCheckpointAdapter(ch, points[i], error_margin)
                race_checkpoints.append(cp)
        race_checkpoints = getattr(self, '_distances_for_' + rtask[
            'race_type'])(race_checkpoints)
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


