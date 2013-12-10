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
        self.assertEqual(len(repr(id)), 55)
        r = repr(id).split(' ')[0]
        self.assertEqual(r, '<DomainIdentifier')

    def test_repr_diid(self):
        id = model.DomainIdentifier(model.DomainIdentifier())
        self.assertIsInstance(repr(id), str)

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


class Test(model.ValueObject):
    three = 3

    def __init__(self, one, two):
        self._one = one
        self.two = two

    @property
    def one(self):
        return self._one

    def four(self):
        return 4

    @staticmethod
    def five():
        return 5

    @classmethod
    def create(cls):
        return Test(1, 2)


class TestValueObjectReadOnly(unittest.TestCase):
    def setUp(self):
        self.t = Test(1, 2)

    def tearDown(self):
        del self.t

    def test_get_private(self):
        self.assertEqual(self.t._one, 1)

    def test_get_class_variable(self):
        self.assertEqual(self.t.three, 3)

    def test_get_property(self):
        self.assertEqual(self.t.one, 1)

    def test_get_attribute(self):
        self.assertEqual(self.t.two, 2)

    def test_set_property(self):
        self.assertRaises(AttributeError, setattr, self.t, 'one', 'new')

    def test_get_method(self):
        self.assertEqual(self.t.four(), 4)

    def test_set_class_variable(self):
        self.assertRaises(AttributeError, setattr, self.t, 'three', 'new')

    def test_set_private(self):
        self.t._one = 'new'
        self.assertEqual(self.t._one, 'new')

    def test_set_attribute(self):
        self.assertRaises(AttributeError, setattr, self.t, 'two', 'new')

    def test_replace_method(self):
        self.t.four = 'new'
        self.assertEqual(self.t.four, 'new')

    def test_call_staticmethod(self):
        self.assertEqual(self.t.five(), 5)

    def test_call_classmethod(self):
        self.assertIsInstance(Test.create(), Test)


class Test2(model.ValueObject):
    def __init__(self, two, one):
        self._one = one
        self.two = two
    @property
    def one(self):
        return self._one


class Test3(model.ValueObject):
    a = Test(1, 2)
    def __init__(self, one, two):
        self.one = one
        self.two = Test(1, two)


class SlottedTest(Test):
    __slots__ = ['one', 'three']


class TestValueObjectEquality(unittest.TestCase):
    def test_same_class(self):
        self.assertEqual(Test(1, range(2)), Test(1, range(2)))

    def test_different_class(self):
        t2 = Test2(2, 1)
        t2.three = 3
        t1 = Test(1, 2)
        self.assertEqual(t1, t2)

    def test_with_value_objects(self):
        self.assertEqual(Test3(1, 'two'), Test3(1, 'two'))

    def test_slotted(self):
        self.assertEqual(SlottedTest(1, 2), SlottedTest(1, 2))


class TestValueObjectNonEquality(unittest.TestCase):
    def test_different_class(self):
        self.assertNotEqual(Test(1, 2), Test2(1, 2))

    def test_same_class_modified_attributes(self):
        t = Test(range(5), 2)
        t._one[1] = 10
        self.assertNotEqual(t, Test(range(5), 2))

    def test_same_class(self):
        self.assertNotEqual(Test(1, 2), Test(2, 1))

    def test_same_class_modified(self):
        t = Test(1, 2)
        del t._one
        self.assertNotEqual(Test(1, 2), t)

    def test_with_value_objects(self):
        self.assertNotEqual(Test3(2, 'two'), Test3(1, 'to'))

    def test_slotted(self):
        self.assertNotEqual(SlottedTest(2, 2), SlottedTest(1, 2))


class TestValueObjectHashability(unittest.TestCase):
    def test_unhashable(self):
        self.assertRaises(TypeError, hash, Test(1, 2))


class Ent(model.Entity):
    def __init__(self, id):
        self.id = id


class TestEntity(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(Ent(1), Ent(1))

    def test_nonequality(self):
        self.assertNotEqual(Ent(range(2)), Ent(range(4)))

    def test_hashability(self):
        t = Ent('a')
        dict(t=1)


if __name__ == '__main__':
    unittest.main()
