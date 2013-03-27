'''
Aggregate Race.
'''

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
    pass

class RaceToGoalTask(RaceTask):
    type = 'racetogoal'
    pass

class OpenDistanceTask(RaceTask):
    type = 'opendistance'
    pass

RACETASKS = {'speedrun': SpeedRunTask,
             'racetogoal': RaceToGoalTask,
             'opendistance': OpenDistanceTask}

class RaceID(IdentifierObject):
    pass


class CheckpointsAreAddedToRace(DomainEvent):
    def __init__(self, id, checkpoints):
        self.checkpoints = checkpoints
        DomainEvent.__init__(self, id)


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
        old_checkpoints = self._checkpoints[::]
        self._checkpoints = checkpoints
        if not (self._invariants_are_correct() and
                self.task.checkpoints_are_good(checkpoints)):
            self._rollback_set_checkpoints(old_checkpoints)
            raise ValueError("Incorrect checkpoints.")
        self.event_publisher.publish(CheckpointsAreAddedToRace(self.id,
                                                                checkpoints))

    def _invariants_are_correct(self):
        return True

    def _rollback_set_checkpoints(self, old_checkpoints):
        pass
