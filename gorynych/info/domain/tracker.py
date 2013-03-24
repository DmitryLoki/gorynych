'''
Tracker Aggregate.
'''
from gorynych.common.domain.model import AggregateRoot, ValueObject, \
    DomainEvent
from gorynych.common.infrastructure.messaging import DomainEventsPublisher


DEVICE_TYPES = ['tr203']

class TrackerAssigned(DomainEvent):

    def __init__(self, id=None, tracker_id=None):
        if not isinstance(tracker_id, TrackerID):
            raise AttributeError("Wrong tracker id.")
        else:
            self.tracker_id = tracker_id

        DomainEvent.__init__(self, id)

    def __eq__(self, other):
        return self.id == other.id and self.timestamp == other.timestamp and (
            self.tracker_id == other.tracker_id)


class TrackerUnAssigned(TrackerAssigned):
    pass


class TrackerHasOwner(Exception):
    pass

class TrackerDontHasOwner(Exception):
    pass


class TrackerID(ValueObject):
    def __init__(self, id=None):
        self.__id = int(id)

    def __repr__(self):
        return self.__id

    def __str__(self):
        return "Tracker-%s" % self.__id

    def __eq__(self, other):
        return self.__id == other


class Tracker(AggregateRoot):

    event_publisher = DomainEventsPublisher()

    def __init__(self, tracker_id, device_id, device_type):
        self.id = tracker_id
        self.device_id = device_id
        self.device_type = device_type
        self.assignee_id = None
        self._name = ''

    @property
    def assignee(self):
        return self.assignee_id

    @assignee.setter
    def assignee(self, value):
        raise AttributeError("Assignee must be setted through assign_to"
                             "(assignee_id) method. ")

    def is_free(self):
        return self.assignee_id is None

    def assign_to(self, assignee_id):
        if self.is_free():
            self.assignee_id = assignee_id
            self.event_publisher.publish(TrackerAssigned(
                id = assignee_id,
                tracker_id = self.id
                ))
        else:
            raise TrackerHasOwner("Tracker has owner: %s" % self.assignee_id)

    def unassign(self):
        if self.is_free():
            raise TrackerDontHasOwner("Tracker isn't assigned to anyone.")
        else:
            _ass_id = self.assignee_id
            self.assignee_id = None
            self.event_publisher.publish(TrackerUnAssigned(id=_ass_id,
                tracker_id=self.id))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, str):
            self._name = value
        else:
            raise TypeError("Tracker name must be string.")



class TrackerFactory(object):

    def __init__(self, event_publisher):
        self.event_publisher = event_publisher

    def create_tracker(self, tracker_id=None, device_id=None,
                       device_type=None, name=None):
        if not isinstance(tracker_id, TrackerID):
            tracker_id = TrackerID(tracker_id)
        if isinstance(device_id, str) and device_type in DEVICE_TYPES:
            tracker = Tracker(tracker_id, device_id, device_type)
            tracker.event_publisher = self.event_publisher
            if isinstance(name, str):
                tracker.name = name
            return tracker
        else:
            raise ValueError("Wrong values has been passed for tracker "
                             "creation.")
