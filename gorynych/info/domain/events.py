'''
List of domain events in context "info".
'''
from gorynych.common.domain.model import DomainEvent


class ArchiveURLReceived(DomainEvent):
    '''
    Notify processing system that new archive with tracks has been loaded for
    race.
    Event fields are:
    @param id: race id
    @param url: url with track archive.
    '''
    def __init__(self, id, url):
        super(ArchiveURLReceived, self).__init__(id)
        self.url = url


class RaceCheckpointsChanged(DomainEvent):
    '''
    Notify other systems (such as processor) about checkpoints change.
    @todo: think about more explicit name for this event.
    '''
    def __init__(self, id, checkpoints):
        self.checkpoints = checkpoints
        DomainEvent.__init__(self, id)


class ParagliderRegisteredOnContest(DomainEvent):
    '''
    Person with id id registered on contest with id contest_id as paraglider.
    Event is fired to notificate users.
    '''
    def __init__(self, id, contest_id):
        self.contest_id = contest_id
        DomainEvent.__init__(self, id)

    def __eq__(self, other):
        return self.id == other.id and self.timestamp == other.timestamp and (
            self.contest_id == other.contest_id)


class TrackerAssigned(DomainEvent):
    '''
    This event is fired then tracker is assigned to someone.

    Event fields are:
    @param id: id of aggregate to which tracker has been assigned.
    @param tracker_id: tracker id.
    '''

    def __init__(self, id=None, tracker_id=None):
        self.tracker_id = tracker_id

        DomainEvent.__init__(self, id)

    def __eq__(self, other):
        return self.id == other.id and self.timestamp == other.timestamp and (
            self.tracker_id == other.tracker_id)


class TrackerUnAssigned(TrackerAssigned):
    pass