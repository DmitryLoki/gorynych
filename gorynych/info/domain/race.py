'''
Aggregate Race.
'''
from copy import deepcopy

from gorynych.common.domain.model import AggregateRoot, IdentifierObject, ValueObject, DomainEvent
from gorynych.common.domain.types import Checkpoint


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

    @property
    def checkpoints(self):
        return self._checkpoints

    @checkpoints.setter
    def checkpoints(self, checkpoints):
        old_checkpoints = deepcopy(self._checkpoints)
        self._checkpoints = checkpoints
        if not self._invariants_are_correct():
            self._rollback_set_checkpoints(old_checkpoints)
            raise ValueError("Invariants are violated.")
        try:
            self.task.checkpoints_are_good(checkpoints)
        except (TypeError, ValueError) as e:
            self._rollback_set_checkpoints(old_checkpoints)
            raise e
        self.event_publisher.publish(CheckpointsAreAddedToRace(self.id,
                                                                checkpoints))

    def _invariants_are_correct(self):
        has_paragliders = len(self.paragliders) > 0
        has_checkpoints = len(self.checkpoints) > 0
        has_task = issubclass(self.task.__class__, RaceTask)
        return has_paragliders and has_checkpoints and has_task

    def _rollback_set_checkpoints(self, old_checkpoints):
        self._checkpoints = old_checkpoints
