'''
DDD-model specific base classes.
'''
import time
import uuid

from gorynych.common.infrastructure.messaging import DomainEventsPublisher

__author__ = 'Boris Tsema'


# TODO: implement comparison by properties
class ValueObject(object):
    '''
    Base class for value objects.
    '''
    pass


class IdentifierObject(object):
    '''
    Base class for aggregate IDs. By default use uuid4 as id.
    '''

    def __init__(self):
        self._id = str(uuid.uuid4())

    @property
    def id(self):
        return str(self._id)

    @classmethod
    def fromstring(cls, string):
        id = cls()
        if id._string_is_valid_id(str(string)):
            id._id = str(string)
            return id

    def _string_is_valid_id(self, string):
        try:
            uuid.UUID(string)
        except ValueError as error:
            raise ValueError("Bad id string: %r" % error)
        return True

    def __eq__(self, other):
        '''
        Make object comparable by id.
        '''
        if issubclass(other.__class__, IdentifierObject):
            another = str(other.id)
        else:
            another = str(other)
        return str(self._id) == another

    def __ne__(self, other):
        if issubclass(other.__class__, IdentifierObject):
            another = str(other.id)
        else:
            another = str(other)
        return str(self._id) != another

    def __hash__(self):
        '''
        Make IdentifierObject hashable.
        '''
        return hash(self._id)

    def __repr__(self):
        '''
        Make object human-readable in logs.
        '''
        return self._id

    def __len__(self):
        return len(str(self._id))


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
