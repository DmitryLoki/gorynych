'''
Tracker Aggregate.
'''
from zope.interface.interfaces import Interface

from gorynych.common.domain.events import TrackerAssigned, TrackerUnAssigned
from gorynych.common.domain.model import AggregateRoot
from gorynych.info.domain.ids import TrackerID


DEVICE_TYPES = ['tr203']

class ITrackerRepository(Interface):
    def get_by_id(tracker_id):
        '''
        '''
    def save(value):
        '''
        '''


class TrackerHasOwner(Exception):
    pass

class TrackerDontHasOwner(Exception):
    pass


class Tracker(AggregateRoot):

    def __init__(self, tracker_id, device_id, device_type):
        super(Tracker, self).__init__()
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
                aggregate_id= assignee_id,
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

    def create_tracker(self, tracker_id=None, device_id=None,
                       device_type=None, name=None):
        if not isinstance(tracker_id, TrackerID):
            tracker_id = TrackerID(device_type, device_id)
        if isinstance(device_id, str) and device_type in DEVICE_TYPES:
            tracker = Tracker(TrackerID(device_type, device_id), device_id,
                device_type)
        else:
            # We have device_id or device_type, and we have tracker_id.
            tracker = Tracker(tracker_id, tracker_id.device_id,
                tracker_id.device_type)

        if isinstance(name, str):
            tracker.name = name.strip()
        return tracker
