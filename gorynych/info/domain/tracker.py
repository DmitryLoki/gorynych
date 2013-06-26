'''
Tracker Aggregate.
'''
from gorynych.common.domain.events import TrackerAssigned, TrackerUnAssigned
from gorynych.common.domain.model import AggregateRoot
from gorynych.info.domain.ids import TrackerID, PersonID
from gorynych.common.infrastructure import persistence as pe


DEVICE_TYPES = ['tr203']


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
            self.assignee_id = PersonID.fromstring(assignee_id)
            return pe.event_store().persist(TrackerAssigned(
                aggregate_id=self.assignee_id,
                payload = self.id))
        else:
            raise RuntimeError("Tracker already has owner: %s" %
                               self.assignee_id)

    def unassign(self):
        if self.is_free():
            raise RuntimeError("Tracker don't assigned to anyone.")
        else:
            aid, self.assignee_id = self.assignee_id, None
            aid = PersonID.fromstring(aid)
            return pe.event_store().persist(TrackerUnAssigned(
                aggregate_id=aid, payload=self.id))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value.strip()


class TrackerFactory(object):

    def create_tracker(self, tracker_id=None, device_id=None,
                       device_type=None, name=None, assignee=None):
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
        if assignee and assignee == 'None':
            assignee = None
        tracker.assignee_id = assignee
        return tracker


def change_tracker(trckr, params):
    '''
    Change some tracker properties.
    @param trckr:
    @type trckr: C{Tracker}
    @param params:
    @type params: C{dict}
    @return: changed (or not) tracker
    @rtype: C{Tracker}
    '''
    if params.has_key('name'):
        trckr.name = params['name']
    if params.has_key('assignee'):
        if params['assignee']:
            trckr.assign_to(params['assignee'])
        else:
            trckr.unassign()
    return trckr
