'''
Aggregate Race.
'''
from copy import deepcopy
import pytz
import decimal

from zope.interface.interfaces import Interface

from gorynych.common.domain.model import AggregateRoot, IdentifierObject, ValueObject, DomainEvent
from gorynych.common.domain.types import Checkpoint
from gorynych.common.exceptions import BadCheckpoint


class RaceTask(ValueObject):
    type = None

    def checkpoints_are_good(self, checkpoints):
        if not checkpoints:
            raise ValueError("Race can't be created without checkpoints.")
        for checkpoint in checkpoints:
            if not isinstance(checkpoint, Checkpoint):
                raise TypeError("Wrong checkpoint type.")
        return True


class SpeedRunTask(RaceTask):
    type = 'speedrun'

class RaceToGoalTask(RaceTask):
    type = 'racetogoal'

class OpenDistanceTask(RaceTask):
    type = 'opendistance'

RACETASKS = {'speedrun': SpeedRunTask,
             'racetogoal': RaceToGoalTask,
             'opendistance': OpenDistanceTask}

class RaceID(IdentifierObject):
    pass


class CheckpointsAreAddedToRace(DomainEvent):
    '''
    Notify other systems (such as processor) about checkpoints change.
    @todo: think about more explicit name for this event.
    '''
    def __init__(self, id, checkpoints):
        self.checkpoints = checkpoints
        DomainEvent.__init__(self, id)

    def __eq__(self, other):
        # TODO: do correct event comparison
        return self.id == other.id and self.timestamp == other.timestamp


class Race(AggregateRoot):
    def __init__(self, id):
        self.id = id

        self.task = None
        self._checkpoints = []
        self.title = ''
        self.timelimits = ()
        self.paragliders = dict()
        self._start_time = decimal.Decimal('infinity')
        self._end_time = 1
        self._timezone = pytz.utc

    @property
    def type(self):
        return self.task.type

    @property
    def bearing(self):
        result = None
        try:
            result = self.task.bearing
        except AttributeError:
            pass
        return result

    @property
    def start_time(self):
        '''
        Time on which race begun.
        @return: Epoch time in seconds.
        @rtype: C{int}
        '''
        return self._start_time

    @property
    def end_time(self):
        '''
        Time when race is ended
        @return: Epoch time in seconds.
        @rtype: C{int}
        '''
        return self._end_time

    @property
    def timezone(self):
        '''
        Race timezone
        @return: string like 'Europe/Moscow'
        @rtype: str
        '''
        return self._timezone

    @timezone.setter
    def timezone(self, value):
        '''
        Set race timezone.
        @param value: string with time zone like 'Europe/Moscow'
        @type value: str
        '''
        if value in pytz.common_timezones_set:
            self._timezone = value

    @property
    def checkpoints(self):
        return self._checkpoints

    @checkpoints.setter
    def checkpoints(self, checkpoints):
        '''
        Replace race checkpoints with a new list. Publish L{
        CheckpointsAreAddedToRace} event with race id and checkpoints list.
        @param checkpoints: list of L{Checlpoint} instances.
        @type checkpoints: C{list}
        '''
        old_checkpoints = deepcopy(self._checkpoints)
        self._checkpoints = checkpoints
        if not self._invariants_are_correct():
            self._rollback_set_checkpoints(old_checkpoints)
            raise ValueError("Race invariants are violated.")
        try:
            self.task.checkpoints_are_good(checkpoints)
        except (TypeError, ValueError) as e:
            self._rollback_set_checkpoints(old_checkpoints)
            raise e
        self._get_times_from_checkpoints(self._checkpoints)
        # Notify other systems about checkpoints changing.
        self.event_publisher.publish(CheckpointsAreAddedToRace(self.id,
                                                                checkpoints))

    def _invariants_are_correct(self):
        has_paragliders = len(self.paragliders) > 0
        has_checkpoints = len(self.checkpoints) > 0
        has_task = issubclass(self.task.__class__, RaceTask)
        return has_paragliders and has_checkpoints and has_task

    def _rollback_set_checkpoints(self, old_checkpoints):
        self._checkpoints = old_checkpoints

    def _get_times_from_checkpoints(self, checkpoints):
        start_time = self._start_time
        end_time = self._end_time
        for point in checkpoints:
            if point.open_time and point.open_time < start_time:
                start_time = point.open_time
            if point.close_time and point.close_time > end_time:
                end_time = point.close_time
        if start_time < end_time:
            self._start_time = start_time
            self._end_time = end_time
        else:
            raise BadCheckpoint("Wrong or absent times in checkpoints.")


class IRaceRepository(Interface):
    def get_by_id(id):
        '''

        @param id:
        @type id:
        @return:
        @rtype:
        '''

    def save(obj):
        '''

        @param obj:
        @type obj:
        @return:
        @rtype:
        '''