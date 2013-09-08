'''
Tracker Aggregate.
'''
from gorynych.common.domain.events import TrackerAssigned, TrackerUnAssigned
from gorynych.common.domain.model import AggregateRoot
from gorynych.info.domain.ids import TrackerID, PersonID, TransportID
from gorynych.common.infrastructure import persistence as pe
from gorynych.common.exceptions import DomainError


DEVICE_TYPES = ['tr203', 'telt_gh3000', 'new_mobile', 'mobile']


class Tracker(AggregateRoot):

    def __init__(self, tracker_id, device_id, device_type):
        super(Tracker, self).__init__()
        self.id = tracker_id
        self.device_id = device_id
        self.device_type = device_type
        self.assignee = dict() # {contest_id:assignee_id}
        self._name = ''
        self._last_point = dict()

    @property
    def last_point(self):
        return [self._last_point.get('lat'), self._last_point.get('lon'),
                    self._last_point.get('alt'), self._last_point.get('ts'),
            self._last_point.get('bat'), self._last_point.get('speed')]

    @last_point.setter
    def last_point(self, value):
        lat, lon, alt, ts, bat, speed = value
        self._last_point['lat'] = lat
        self._last_point['lon'] = lon
        self._last_point['alt'] = alt
        self._last_point['ts'] = ts
        self._last_point['bat'] = bat
        self._last_point['speed'] = speed

    def is_free(self):
        return len(self.assignee) == 0

    def assign_to(self, assignee_id, contest_id):
        assignee_type = assignee_id.split('-', 1)[0]
        if assignee_type == 'pers':
            assignee_id = PersonID.fromstring(assignee_id)
        elif assignee_type == 'trns':
            assignee_id = TransportID.fromstring(assignee_id)
        if contest_id in self.assignee.keys():
            raise DomainError("Tracker already has owner %s for "
                               "contest %s" %
                               (self.assignee.get(contest_id), contest_id))
        self.assignee[contest_id] = assignee_id
        return pe.event_store().persist(TrackerAssigned(
            aggregate_id=assignee_id,
            payload = (str(self.id), str(contest_id))))

    def unassign(self, contest_id):
        if self.is_free():
            raise DomainError("Tracker isn't assigned to anyone.")
        elif not self.assignee.has_key(contest_id):
            raise DomainError("Tracker hasn't been assigned to contest %s" %
                              contest_id)
        else:
            aid = self.assignee[contest_id]
            del self.assignee[contest_id]
            assignee_type = aid.split('-', 1)[0]
            if assignee_type == 'pers':
                aid = PersonID.fromstring(aid)
            elif assignee_type == 'trns':
                aid = TransportID.fromstring(aid)
            return pe.event_store().persist(TrackerUnAssigned(
                aggregate_id=aid, payload=(str(self.id), str(contest_id))))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value.strip()


class TrackerFactory(object):

    def create_tracker(self, tracker_id=None, device_id=None,
                       device_type=None, name=None, assignee=None,
            last_point=None):
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
        if assignee:
            tracker.assignee = assignee
        else:
            tracker.assignee = dict()

        if isinstance(last_point, tuple) and len(last_point) == 6:
            tracker.last_point = last_point
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
    if params.has_key('assignee') and params.has_key('contest_id'):
        if params['assignee']:
            trckr.assign_to(params['assignee'], params['contest_id'])
        else:
            trckr.unassign(params['contest_id'])
    return trckr
