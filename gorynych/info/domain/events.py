'''
List of domain events in context "info".
'''
from gorynych.common.domain.model import DomainEvent

class ArchiveURLReceived(DomainEvent):
    '''
    New archive with tracks has been loaded for race.
    '''
    def __init__(self, id, url):
        super(ArchiveURLReceived, self).__init__(id)
        self.url = url


class CheckpointsAreAddedToRace(DomainEvent):
    '''
    Notify other systems (such as processor) about checkpoints change.
    @todo: think about more explicit name for this event.
    '''
    def __init__(self, id, checkpoints):
        self.checkpoints = checkpoints
        DomainEvent.__init__(self, id)

