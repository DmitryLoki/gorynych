'''
Store events in system according to Event Sourcing pattern.
'''
from datetime import datetime
import time

from zope.interface import implementer

from gorynych.eventstore.interfaces import IEventStore
from gorynych.common.domain import events


@implementer(IEventStore)
class EventStore(object):
    def __init__(self, store):
        '''

        @param store:
        @type store: gorynych.eventstore.store.PGSQLAppendOnlyStore
        @return:
        @rtype:
        '''
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

    def load_undispatched_events(self):
        d = self.store.load_undispatched_events()
        return d.addCallback(self._construct_event_list)

    def _construct_event_list(self, stored_events):
        '''
        Create EventStream instance from a list of stored events.
        @param stored_events: list of tuples from db
        @type stored_events: C{list}
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
        @rtype: instance of DomainEvent subclass
        '''
        id, name, aggrid, aggrtype, payload, ts = stored_event
        event_class = getattr(events, name)
        if event_class:
            event = event_class(aggrid, aggregate_type=aggrtype,
                        occured_on=int(time.mktime(ts.timetuple())))
            event.payload = event.serializer.from_bytes(payload)
            event.id = id
            return event

    def persist(self, event):
        if isinstance(event, list):
            to_store = list()
            for ev in event:
                if ev:
                    to_store.append(self._serialize(ev))
        else:
            to_store = [self._serialize(event)]
        return self.store.append(to_store)

    def _serialize(self, event):
        '''

        @param event:
        @type event: DomainEvent subclass instance.
        @return:
        @rtype: C{dict}
        '''
        result = dict()
        result['occured_on'] = datetime.fromtimestamp(event.occured_on)
        result['event_payload'] = event.serializer.to_bytes(event.payload)
        result['aggregate_type'] = str(event.aggregate_type)
        result['aggregate_id'] = str(event.aggregate_id)
        result['event_name'] = str(event.__class__.__name__)
        return result

    def load_events_for_aggregates(self, elist):
        '''

        @param elist: {aggr_id:row}
        @type elist: C{dict}
        @return: {aggr_id:event_list}
        @rtype: dict
        '''
        def process(e_list):
            result = dict()
            for aggr_id in e_list:
                result[aggr_id] = self._construct_event_list(e_list[aggr_id])
            return result
        d = self.store.load_events_for_aggregates(elist)
        d.addCallback(process)
        return d

