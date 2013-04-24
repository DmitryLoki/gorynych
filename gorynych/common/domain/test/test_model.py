import unittest
import uuid

from gorynych.common.domain import model
from gorynych.common.infrastructure.messaging import DomainEventsPublisher

class IdentifierObjectTest(unittest.TestCase):
    def _get_id(self):
        return model.IdentifierObject()

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
        print other
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

    def test_create_from_string(self):
        string = str(uuid.uuid4())
        id = model.IdentifierObject.fromstring(string)
        self.assertIsInstance(id, model.IdentifierObject)
        self.assertEqual(id.id, string)

    def test_create_from_string_bad_case(self):
        self.assertRaises(ValueError, model.IdentifierObject.fromstring,
                          'hello')

class AggregateRootTest(unittest.TestCase):
    def test_init(self):
        ar = model.AggregateRoot()
        self.assertIsNone(ar._id)
        ar._id = 1
        self.assertIsNotNone(ar._id)
        self.assertIsInstance(ar.event_publisher, DomainEventsPublisher)

if __name__ == '__main__':
    unittest.main()
