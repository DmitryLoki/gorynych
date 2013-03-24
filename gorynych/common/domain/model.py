'''
DDD-model specific base classes.
'''
import time

__author__ = 'Boris Tsema'

class Event(object):
    pass


class ValueObject(object):
    pass

class AggregateRoot(object):
    pass


class DomainEvent(object):
    def __init__(self, id=None):
        if not id:
            raise AttributeError("No event owner id.")
        else:
            self.id = id
        self.timestamp = int(time.time())
