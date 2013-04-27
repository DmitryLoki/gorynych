'''
Store events in system according to Event Sourcing pattern.
'''
import sys
from datetime import datetime
import simplejson as json

from zope.interface import implementer

from gorynych.eventstore.interfaces import IEventStore
from gorynych.info.domain import events


@implementer(IEventStore)
class EventStore(object):
    def __init__(self, store):
        self.store = store

    def load_events(self, id, from_version=0, to_version=sys.maxint):
        '''

        @param id:
        @type id:
        @param from_version:
        @type from_version:
        @param to_version:
        @type to_version:
        @return:
        @rtype: C{EventStream} subclass.
        '''
        d = self.store.load_events(id, from_version, to_version)
        return d.addCallback(self._construct_event_list)

    def _construct_event_list(self, stored_events):
        '''
        Create EventStream instance from a list of stored events.
        @param stored_events:
        @type stored_events:
        @return:
        @rtype:
        '''
        if stored_events:
            result = []
            for idx, stored_event in enumerate(stored_events):
                event = self._deserialize(stored_event)
                result.append(event)
            return result

    def _deserialize(self, stored_event):
        '''

        @param stored_event:
        @type stored_event: C{tuple}
        @return:
        @rtype: instance of L{DomainEvent} subclass
        '''
        _, name, aggrid, aggrtype, payload, ts, _ = stored_event
        event_class = getattr(events, name)
        if event_class:
            event = event_class(aggrid, aggregate_type=aggrtype,
                                occured_on=ts)
            event.payload = event.serializer.from_bytes(payload)
            return event

    def persist(self, event):
        serialized_event = self._serialize(event)
        return self.store.append(serialized_event)

    def _serialize(self, event):
        '''

        @param event:
        @type event: L{DomainEvent} subclass instance.
        @return:
        @rtype: C{dict}
        '''
        result = json.loads(str(event))
        result['occured_on'] = datetime.fromtimestamp(result['occured_on'])
        result['event_payload'] = event.serializer.to_bytes(event.payload)
        return result

