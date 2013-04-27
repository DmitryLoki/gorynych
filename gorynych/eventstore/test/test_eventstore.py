from datetime import datetime

import mock
from twisted.trial import unittest
from zope.interface.verify import verifyObject

from gorynych.eventstore.interfaces import IEventStore
from gorynych.eventstore.eventstore import EventStore
from gorynych.common.domain.model import  DomainEvent, DomainIdentifier
from gorynych.common.infrastructure.serializers import StringSerializer


class TestEvent(DomainEvent):
    serializer = StringSerializer()

def create_event(id=None):
    if not id:
        id = DomainIdentifier()
    ts = 123
    aggtype = 'a_type'
    payload = 'payload'
    return TestEvent(id, payload, aggtype, ts)


class EventStoreTest(unittest.TestCase):
    def setUp(self):
        self.store = mock.Mock()

    def test_0_validate_class(self):
        es = EventStore(self.store)
        verifyObject(IEventStore, es)

    def test_1_serialize(self):
        event = create_event()
        es = EventStore(self.store)
        ser_event = es._serialize(event)

        self.assertIsInstance(ser_event, dict, "Serialized event not a dict.")
        self.assertIsInstance(ser_event['occured_on'], datetime)
        self.assertIsInstance(ser_event['event_payload'], bytes)

        columns = ['event_name', 'aggregate_id',
                   'aggregate_type', 'event_payload', 'occured_on']
        for col in columns:
            self.assertTrue(ser_event.has_key(col), "Event missed a key %s"
                                                    % col)

    def test_2_persist(self):
        es = EventStore(self.store)
        event = create_event()
        result = es.persist(event)
        self.assertTrue(es.store.append.called)


