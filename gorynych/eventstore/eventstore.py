'''
Store events in system according to Event Sourcing pattern.
'''
from datetime import datetime
import time
import simplejson as json

from zope.interface import implementer

from gorynych.eventstore.interfaces import IEventStore
from gorynych.info.domain import events


@implementer(IEventStore)
class EventStore(object):
    def __init__(self, store):
        self.store = store

    def load_events(self, id):
        '''

        @param id: identificator of aggregate for which to load events.
        @type id: C{DomainIdentifier} subclass.
        @return: list of events.
        @rtype: C{list}.
        '''
        d = self.store.load_events(str(id))
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
        id, name, aggrid, aggrtype, payload, ts = stored_event
        event_class = getattr(events, name)
        if event_class:
            event = event_class(aggrid, aggregate_type=aggrtype,
                        occured_on=int(time.mktime(ts.timetuple())))
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

