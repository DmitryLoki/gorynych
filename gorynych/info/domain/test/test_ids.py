import uuid
from datetime import date
from sys import getsizeof

from twisted.trial import unittest

from gorynych.info.domain.ids import ContestID, \
    namespace_date_random_validator, namespace_uuid_validator


class ContestIDTest(unittest.TestCase):
    def _get_id(self):
        return ContestID()

    def test_aggregate_type(self):
        self.assertEqual('cnts', self._get_id().id.split('-')[0])

    def test_date(self):
        id = self._get_id().id
        d = date.today().strftime('%y%m%d')
        self.assertEquals(d, id.split('-')[1])

    def test_random(self):
        id = self._get_id().id
        self.assertEqual(getsizeof(int(id.split('-')[-1])), 24)

    def test_create_from_string(self):
        r_field = str(uuid.uuid4().fields[0])
        string = 'cnts-120203-' + r_field
        id = ContestID.fromstring(string)
        self.assertIsInstance(id, ContestID)
        self.assertEqual(id.id, string)

    def test_bad_creation_from_string(self):
        string = 'c'
        self.assertRaises(ValueError, ContestID.fromstring, string)
        string = 'cnt-120203-12345'
        self.assertRaises(AssertionError, ContestID.fromstring,
                          string)
        string = 'cnts-1201-12345'
        self.assertRaises(AssertionError, ContestID.fromstring,
                          string)
        string = 'cnts-120203-abr'
        self.assertRaises(ValueError, ContestID.fromstring, string)


class ValidatorsTest(unittest.TestCase):
    def test_namespace_date_random_validator(self):
        r_field = str(uuid.uuid4().fields[0])
        string = 'cnts-120203-' + r_field
        self.assertTrue(namespace_date_random_validator(string, 'cnts'))
        self.assertRaises(AssertionError, namespace_date_random_validator,
                          string, 'hello')
        badstring = 'cnts-12324-' + r_field
        self.assertRaises(AssertionError, namespace_date_random_validator,
                          badstring, 'cnts')
        anotherbadstring = 'cnts-120203-hahaha'
        self.assertRaises(ValueError, namespace_date_random_validator,
                          anotherbadstring, 'cnts')

    def test_namespace_uuid_validator(self):
        _id = str(uuid.uuid4())
        string = 'haha-'+_id
        self.assertTrue(namespace_uuid_validator(string, 'haha'))
        self.assertRaises(ValueError, namespace_uuid_validator,
                          string[:15], 'haha')