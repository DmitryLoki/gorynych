from twisted.trial import unittest
import uuid
from datetime import date
from sys import getsizeof

from gorynych.info.domain.ids import ContestID


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

