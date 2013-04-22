'''
Store events in system according to Event Sourcing pattern.
'''
import sys

from zope.interface import implementer

from gorynych.eventstore.interfaces import IEventStore


@implementer(IEventStore)
class EventStore(object):
    def __init__(self, store):
        self.store = store

    def load_event_stream(self, id, from_version=0, to_version=sys.maxint):
        return self.store.read_records(id, from_version, to_version)


