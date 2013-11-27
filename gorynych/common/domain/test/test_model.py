import unittest
import time
import uuid

import mock
from zope.interface.verify import verifyObject
from zope.interface.exceptions import DoesNotImplement

from gorynych.common.domain import model
from gorynych.eventstore.interfaces import IEvent


class TestID(model.DomainIdentifier): pass


class IdentifierObjectTest(unittest.TestCase):
    def _get_id(self):
        return model.DomainIdentifier()

    def test_hash(self):
        id = self._get_id()
        a = {id: '1'}
        self.assertEqual(a[id], '1')

    def test_equal_identifier_object(self):
        id = self._get_id()
        self.assertEqual(id, id)

    def test_equal_string(self):
        id = self._get_id()
        other = id.id
        self.assertEqual(id, other)

    def test_not_equal_identifier_object(self):
        id_1 = self._get_id()
        id_2 = self._get_id()
        self.assertNotEqual(id_1, id_2)

    def test_not_equal_string(self):
        id_1 = self._get_id()
        other = 'hello'
        self.assertNotEqual(id_1, other)

    def test_len(self):
        id = self._get_id()
        self.assertEqual(len(id), 36)

    def test_repr(self):
        id = self._get_id()
        self.assertIsInstance(repr(id), str)
        self.assertEqual(len(repr(id)), 36)

    def test_str(self):
        uid = str(uuid.uuid4())
        id = model.DomainIdentifier.fromstring(uid)
        self.assertEqual(str(id), uid)

    def test_create_from_string(self):
        string = str(uuid.uuid4())
        id = model.DomainIdentifier.fromstring(string)
        self.assertIsInstance(id, model.DomainIdentifier)
        self.assertEqual(id.id, string)

    def test_create_from_string_bad_case(self):
        self.assertRaises(ValueError, model.DomainIdentifier.fromstring,
                          'hello')

    def test_create_from_domainidentifier(self):
        _id = TestID()
        di = TestID(_id)
        self.assertTrue(_id == di)

    def test_create_from_domainidentifier_bad_case(self):
        _id = TestID()
        _id._id = _id._id[:-3]
        self.assertRaises(ValueError, TestID, _id)

    def test_create_from_another_domainidentifier(self):
        _id = TestID()
        class TestID2(model.DomainIdentifier):pass
        self.assertRaises(ValueError, TestID2, _id)

    def test_init_with_string(self):
        string = str(uuid.uuid4())
        _id = model.DomainIdentifier(string)
        self.assertIsInstance(_id, model.DomainIdentifier)
        self.assertEqual(_id.id, string)

    def test_init_with_string_bad_case(self):
        self.assertRaises(ValueError, model.DomainIdentifier, 'hello')


class DomainEventTest(unittest.TestCase):
    def test_success_creation(self):
        ts = int(time.time())
        event = model.DomainEvent(1, 2, 'hello', ts)
        verifyObject(IEvent, event)
        self.assertTupleEqual(('1', 2, 'hello', ts), (event.aggregate_id,
                    event.payload, event.aggregate_type, event.occured_on))

    def test_creation_with_identifier_object(self):
        id = TestID()
        ev, ts = model.DomainEvent(id, 'payload'), int(time.time())
        self.assertTupleEqual((id.id, 'payload', 'test', ts),
              (ev.aggregate_id, ev.payload, ev.aggregate_type, ev.occured_on))

    def test_equality(self):
        ts = int(time.time())
        ev1 = model.DomainEvent(1, 2, 'hello', ts)
        ev2 = model.DomainEvent(1, 2, 'hello', ts)
        self.assertEqual(ev1, ev2)

    def test_non_equality(self):
        ts = int(time.time())
        ev1 = model.DomainEvent(1, 2, 'hello', ts)
        ev2 = model.DomainEvent(1, 3, 'hello', ts)
        self.assertNotEqual(ev1, ev2)
        ev2 = model.DomainEvent(2, 2, 'hello', ts)
        self.assertNotEqual(ev1, ev2)
        ev2 = model.DomainEvent(1, 2, 'ello', ts)
        self.assertNotEqual(ev1, ev2)
        ev2 = model.DomainEvent(1, 2, 'hello', ts+1)
        self.assertNotEqual(ev1, ev2)

    def test_repr(self):
        ts = int(time.time())
        ev1 = model.DomainEvent(1, IdentifierObjectTest, 'hello', ts)
        self.assertIsInstance(repr(ev1), str)

    def test_str(self):
        ts = int(time.time())
        ev1 = model.DomainEvent(1, 1, 'hello', ts)
        result = dict(event_name="DomainEvent",
                      aggregate_id='1',
                      aggregate_type='hello',
                      event_payload='1',
                      occured_on=ts)
        self.assertEqual(str(ev1), str(result))


class AggregateRootTest(unittest.TestCase):
    def test_init(self):
        ar = model.AggregateRoot()
        self.assertIsNone(ar._id)
        ar._id = 1
        self.assertIsNotNone(ar._id)

    def test_apply(self):
        ar = model.AggregateRoot()
        ar.apply_DomainEvent = mock.Mock()
        _id = model.DomainIdentifier()
        de = model.DomainEvent(_id)
        self.assertRaises(AssertionError, ar.apply, 1)
        self.assertRaises(DoesNotImplement, ar.apply, [1])

        class Event(model.DomainEvent):
            pass

        ar.apply([Event(_id)])
        self.assertFalse(ar.apply_DomainEvent.called)

        ar.apply([de])
        ar.apply_DomainEvent.assert_called_once_with(de)

    def test_apply_none(self):
        ar = model.AggregateRoot()
        ar.apply(None)

if __name__ == '__main__':
    unittest.main()
