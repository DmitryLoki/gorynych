import math
import types

import numpy as np
from zope.interface import implementer

from gorynych.common.domain import events
from gorynych.common.domain.types import checkpoint_collection_from_geojson
from gorynych.common.domain.services import point_dist_calculator, bearing
from gorynych.processor.domain import services
from gorynych.processor.interfaces import IRaceType


@implementer(IRaceType)
class RaceToGoal(object):
    '''
    Incapsulate race parameters calculation.
    '''
    type = 'racetogoal'

    def __init__(self, task, checkpoints):
        self.checkpoints = checkpoints
        self.start_time = int(task['start_time'])
        self.end_time = int(task['end_time'])

    def process(self, points, trackstate, _id):
        '''
        Process points and emit events if needed.
        @param points: array with points for some seconds (minute usually).
        @type points: C{np.array}
        @param trackstate: read-only object implementing track state.
        @type trackstate: gorynych.processor.domain.track.TrackState
        @return: (points, event list)
        @rtype: (np.array, list)
        '''
        assert isinstance(points, np.ndarray), "Got %s instead of ndarray" % \
                                               type(points)
        eventlist = []
        lastchp = trackstate.last_checkpoint
        if lastchp < len(self.checkpoints) - 1:
            nextchp = self.checkpoints[lastchp + 1]
        else:
            # Last point has been taken but we still have data.
            if trackstate.last_distance:
                for p in points:
                    p['distance'] = trackstate.last_distance
                return points, []
            else:
                for p in points:
                    p['distance'] = 200
                return points, []
        if trackstate.state == 'landed':
            if trackstate.last_distance:
                for p in points:
                    p['distance'] = trackstate.last_distance
                return points, []
            else:
                for p in points:
                    p['distance'] = 200
                return points, []

        calculation_ended = trackstate.ended
        for idx, p in np.ndenumerate(points):
            lat, lon = p['lat'], p['lon']
            if nextchp.is_taken_by(lat, lon, p['timestamp']) and \
                    (not calculation_ended):
                eventlist.append(
                    events.TrackCheckpointTaken(
                        _id,
                        (lastchp + 1, nextchp.dist_to_center),
                        occured_on=nextchp.take_time))
                if nextchp.type == 'es':
                    eventlist.append(events.TrackFinishTimeReceived(_id,
                        payload=p['timestamp']))
                if nextchp.type == 'goal':
                    eventlist.append(events.TrackFinished(_id,
                        occured_on=trackstate.finish_time))
                    calculation_ended = True
                if nextchp.type == 'ss':
                    eventlist.append(events.TrackStarted(_id,
                        occured_on=p['timestamp']))
                if lastchp + 1 < len(self.checkpoints) - 1:
                    nextchp = self.checkpoints[lastchp + 2]
                    lastchp += 1
            p['distance'] = nextchp.dist_to_point(lat, lon) + nextchp.distance

        return points, eventlist


@implementer(IRaceType)
class SpeedRun(object):
    type = 'speedrun'

    def __init__(self, task, checkpoints):
        self.checkpoints = checkpoints
        self.start_time = int(task['start_time'])
        self.end_time = int(task['end_time'])

    def process(self, points, trackstate, _id):
        '''
        Process points and emit events if needed.
        @param points: array with points for some seconds (minute usually).
        @type points: C{np.array}
        @param trackstate: read-only object implementing track state.
        @type trackstate: gorynych.processor.domain.track.TrackState
        @return: (points, event list)
        @rtype: (np.array, list)
        '''
        assert isinstance(points, np.ndarray), "Got %s instead of ndarray" % \
                                               type(points)
        eventlist = []
        lastchp = trackstate.last_checkpoint
        if lastchp < len(self.checkpoints) - 1:
            nextchp = self.checkpoints[lastchp + 1]
        else:
            # Last point has been taken but we still have data.
            if trackstate.last_distance:
                for p in points:
                    p['distance'] = trackstate.last_distance
                return points, []
            else:
                for p in points:
                    p['distance'] = 200
                return points, []
        if trackstate.state == 'landed':
            if trackstate.last_distance:
                for p in points:
                    p['distance'] = trackstate.last_distance
                return points, []
            else:
                for p in points:
                    p['distance'] = 200
                return points, []

        calculation_ended = trackstate.ended
        for idx, p in np.ndenumerate(points):
            lat, lon = p['lat'], p['lon']
            if nextchp.is_taken_by(lat, lon, p['timestamp']) and \
                    (not calculation_ended):
                eventlist.append(
                    events.TrackCheckpointTaken(
                        _id,
                        (lastchp + 1, nextchp.dist_to_center),
                        occured_on=nextchp.take_time))
                if nextchp.type == 'es':
                    eventlist.append(events.TrackFinishTimeReceived(_id,
                        payload=p['timestamp']))
                if nextchp.type == 'goal':
                    eventlist.append(events.TrackFinished(_id,
                        occured_on=trackstate.finish_time))
                    calculation_ended = True
                if nextchp.type == 'ss':
                    eventlist.append(events.TrackStarted(_id,
                        occured_on=p['timestamp']))
                if lastchp + 1 < len(self.checkpoints) - 1:
                    nextchp = self.checkpoints[lastchp + 2]
                    lastchp += 1
            p['distance'] = nextchp.dist_to_point(lat, lon) + nextchp.distance

        return points, eventlist


@implementer(IRaceType)
class OpenDistance(object):
    type = 'opendistance'

    def __init__(self, task, checkpoints):
        self.checkpoints = checkpoints
        self.task = task
        _bearing = task.get('bearing')
        if not _bearing or _bearing == "None":
            self.bearing = None
        else:
            self.bearing = int(_bearing)
        self.start_time = int(task['start_time'])
        self.end_time = int(task['end_time'])

    def process(self, points, trackstate, _id):
        '''
        Process points and emit events if needed.
        @param points: array with points for some seconds (minute usually).
        @type points: C{np.array}
        @param trackstate: read-only object implementing track state.
        @type trackstate: gorynych.processor.domain.track.TrackState
        @return: (points, event list)
        @rtype: (np.array, list)
        '''
        assert isinstance(points, np.ndarray), "Got %s instead of ndarray" % \
                                               type(points)
        eventlist = []
        lastchp_num = trackstate.last_checkpoint
        lastchp = self.checkpoints[lastchp_num]
        previous_leg = self.checkpoints[lastchp_num].distance

        if self._checkpoint_is_last(lastchp_num):
            return self._calculate_last_leg(points, previous_leg)
        else:
            # Calculate passed distance.
            nextchp = self.checkpoints[lastchp_num + 1]
            for idx, p in np.ndenumerate(points):
                lat, lon = p['lat'], p['lon']
                p['distance'] = previous_leg + lastchp.dist_to_point(lat, lon)
                if nextchp.is_taken_by(lat, lon, p['timestamp']):
                    eventlist.append(
                        events.TrackCheckpointTaken(_id,
                            (lastchp_num + 1, nextchp.dist_to_center),
                            occured_on=nextchp.take_time))
                    if self._checkpoint_is_last(lastchp_num + 1):
                        return self._calculate_last_leg(points,
                            previous_leg, eventlist=eventlist,
                            from_idx=idx[0])
                    else:
                        nextchp = self.checkpoints[lastchp_num + 2]
                        lastchp_num += 1
                        previous_leg = self.checkpoints[lastchp_num].distance

        return points, eventlist

    def _checkpoint_is_last(self, checkpoint_number):
        return checkpoint_number >= len(self.checkpoints) - 1

    def _calculate_last_leg(self, points, previous_leg, eventlist=None,
            from_idx=0):
        chp = self.checkpoints[-1]
        for idx, p in np.ndenumerate(points[from_idx:]):
            lat, lon = p['lat'], p['lon']
            dist = chp.dist_to_point(lat, lon)
            if not self.bearing is None:
                # TODO: distance calculaction should be done in checkpoint.
                dist = int(dist * math.cos(
                    math.radians(bearing(chp.opt_lat, chp.opt_lon, lat, lon)
                    - self.bearing)))
            p['distance'] = previous_leg + dist

        if eventlist is None:
            eventlist = []
        return points, eventlist


def taken_on_enter(self, lat, lon, on_time):
    '''
    Is point (lat, lon) inside the circle?
    @param lat:
    @type lat: float
    @param lon:
    @type lon: float
    @return:
    @rtype: boolean
    '''
    self.dist_to_center = int(point_dist_calculator(
        lat, lon, self.checkpoint.lat, self.checkpoint.lon))
    is_taken = self.dist_to_center < (
        self.checkpoint.radius + self.error_margin)
    if is_taken:
        self.take_time = on_time
    return is_taken


def taken_on_exit(self, lat, lon, on_time):
    '''
    Point taken then on a cylinder leave.
    @param lat:
    @type lat: float
    @param lon:
    @type lon: float
    @param on_time:
    @type on_time: int
    @return: is cylinder has been taken?
    @rtype: boolean
    '''
    self.dist_to_center = int(point_dist_calculator(
        lat, lon, self.checkpoint.lat, self.checkpoint.lon))
    is_inside = self.dist_to_center < (
        self.checkpoint.radius + self.error_margin)
    cylinder_just_entered = is_inside and not self._point_inside
    point_still_in_cylinder = is_inside and self._point_inside
    cylinder_just_exited = self._point_inside and not is_inside
    if cylinder_just_entered:
        self._point_inside = True
        self.take_time = on_time
        return False
    if cylinder_just_exited:
        self._point_inside = False
        return True
    if point_still_in_cylinder:
        self.take_time = on_time
        return False


class CylinderCheckpointAdapter(object):
    '''
    Adapter for cylinder checkpoints.
    '''
    def __init__(self, chp, opt_point, error_margin):
        '''
        @param chp: checkpoint which to adapt.
        @type chp: gorynych.common.domain.types.Checkpoint.
        @param opt_point: lat, lon of optimum point on Cylinder.
        @type opt_point: tuple
        @param error_margin: acceptable buffer where cylinder can be taken.
        @type error_margin: int
        @return:
        @rtype:
        '''
        self.checkpoint = chp
        self.distance = 0
        self.error_margin = error_margin
        assert len(opt_point) == 2, "Optimum point parameter is wrong."
        assert isinstance(opt_point, tuple), "Need tuple as a point."
        self.opt_lat, self.opt_lon = opt_point
        # Flag shows is point inside the cylinder.
        self._point_inside = False

    def is_taken_by(self, lat, lon, on_time):
        pass

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
        return int(point_dist_calculator(
            lat, lon, self.opt_lat, self.opt_lon))

    @property
    def type(self):
        return self.checkpoint.type


class RaceTypesFactory(object):
    races = dict(racetogoal=RaceToGoal, opendistance=OpenDistance, speedrun=SpeedRun)
    error_margin = dict(online={'es': 10, 'goal': 10, 'default': 1000},
        competition_aftertask={'es': 10, 'goal': 10, 'default': 50})

    def create(self, rtype, rtask):
        '''
        @param rtask: dictionary with race task.
        @type rtask: dict
        @param rtype: string with task type: 'online',
        'competition_aftertask'.
        '''
        assert isinstance(rtask, dict), "Race task must be dict."
        try:
            race = self.races[rtask['race_type']]
        except KeyError:
            raise ValueError("No such race type %s" % rtask.get('race_type'))
        checkpoints = checkpoint_collection_from_geojson(rtask['checkpoints'])
        points, _ = services.JavaScriptShortWay().calculate(checkpoints)
        race_checkpoints = []
        for i, ch in enumerate(checkpoints):
            if ch.geometry.geom_type == 'Point':
                error_margin = self.error_margin[rtype].get(ch.type,
                    self.error_margin[rtype]['default'])
                cp = CylinderCheckpointAdapter(ch, points[i], error_margin)
                if ch.checked_on == 'enter':
                    cp.is_taken_by = types.MethodType(taken_on_enter, cp,
                        CylinderCheckpointAdapter)
                elif ch.checked_on == 'exit':
                    cp.is_taken_by = types.MethodType(taken_on_exit, cp,
                        CylinderCheckpointAdapter)
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

    def _distances_for_opendistance(self, race_checkpoints):
        if len(race_checkpoints) == 1:
            return race_checkpoints
        for idx, p in enumerate(race_checkpoints[1:]):
            dist_from_prev = p.dist_to_point(
                race_checkpoints[idx].opt_lat, race_checkpoints[idx].opt_lon)
            p.distance = race_checkpoints[idx].distance + dist_from_prev
        return race_checkpoints

    def _distances_for_speedrun(self, race_checkpoints):
        if len(race_checkpoints) == 1:
            return race_checkpoints
        for idx, p in enumerate(race_checkpoints[1:]):
            dist_from_prev = p.dist_to_point(
                race_checkpoints[idx].opt_lat, race_checkpoints[idx].opt_lon)
            p.distance = race_checkpoints[idx].distance + dist_from_prev
        return race_checkpoints
