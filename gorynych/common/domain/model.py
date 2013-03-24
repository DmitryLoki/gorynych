'''
DDD-model specific base classes.
'''
import time

from gorynych.common.infrastructure.messaging import DomainEventsPublisher

__author__ = 'Boris Tsema'

class Event(object):
    pass


class ValueObject(object):
    pass


class IdentifierObject(object):

    def __init__(self, id):
        if not id:
            raise AttributeError("No id in IdentifierObject.")
        self.id = id

    def __eq__(self, other):
        if isinstance(other, int) or isinstance(other, str):
            return self.id == other
        elif isinstance(other, IdentifierObject):
            return self.id == other.id

class AggregateRoot(object):
    event_publisher = DomainEventsPublisher()


class DomainEvent(object):
    def __init__(self, id=None):
        if not id:
            raise AttributeError("No event owner id.")
        else:
            self.id = id
        self.timestamp = int(time.time())
