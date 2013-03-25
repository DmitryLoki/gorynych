'''
DDD-model specific base classes.
'''
import time

from gorynych.common.infrastructure.messaging import DomainEventsPublisher

__author__ = 'Boris Tsema'


class ValueObject(object):
    '''
    Base class for value objects.
    '''
    pass


class IdentifierObject(object):
    '''
    Base class for aggregate IDs.
    '''

    def __init__(self, id):
        if not id:
            raise AttributeError("No id in IdentifierObject.")
        self.id = id

    def __eq__(self, other):
        '''
        Make object comparable by id.
        '''
        if isinstance(other, int) or isinstance(other, str):
            return self.id == other
        elif isinstance(other, IdentifierObject):
            return self.id == other.id

    def __hash__(self):
        '''
        Make IdentifierObject hashable.
        '''
        return hash(self.id)

class AggregateRoot(object):
    '''
    Base class for aggregate roots.
    '''
    event_publisher = DomainEventsPublisher()


class DomainEvent(object):
    '''
    Base class for domain events.
    '''
    def __init__(self, id=None):
        if not id:
            raise AttributeError("No event owner id.")
        else:
            self.id = id
        self.timestamp = int(time.time())
