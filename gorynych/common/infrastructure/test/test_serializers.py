from twisted.trial import unittest
from gorynych.info.domain.test.helpers import create_checkpoints

from gorynych.common.infrastructure import serializers
from gorynych.common import exceptions

class DomainIdentifierSerializerTest(unittest.TestCase):
    def test_bytes(self):
        from gorynych.info.domain.ids import ContestID
        s = serializers.DomainIdentifierSerializer('ContestID')
        id = ContestID()
        bts = s.to_bytes(id)
        self.assertIsInstance(bts, bytes)
        self.assertEqual(bts, bytes(id))

        deserialized_id = s.from_bytes(bts)
        self.assertIsInstance(deserialized_id, ContestID)
        self.assertEqual(deserialized_id, id)

    def test_bad_bytes(self):
        self.assertRaises(exceptions.DeserializationError,
                          serializers.DomainIdentifierSerializer,
                          'StangeID')



class GeoObjectsListSerializerTest(unittest.TestCase):
    def test_bytes(self):
        from gorynych.common.domain.types import Checkpoint, checkpoint_from_geojson

        s = serializers.GeoObjectsListSerializer(checkpoint_from_geojson)
        geolist = create_checkpoints()

        bts = s.to_bytes(geolist)
        self.assertIsInstance(bts, bytes)

        from_bts = s.from_bytes(bts)
        self.assertIsInstance(from_bts, list)
        self.assertIsInstance(from_bts[0], Checkpoint)



class JSONSerializerTest(unittest.TestCase):
    def test_to_bytes(self):
        a = [dict(a='b', c='d'), 1, None, 'a', False]
        res = serializers.JSONSerializer().to_bytes(a)
        self.assertIsInstance(res, bytes)


class PickleSerializer(unittest.TestCase):
    def test_test(self):
        import numpy as np
        a = np.arange(5)
        s = serializers.PickleSerializer()
        self.assertTrue((a == s.from_bytes(s.to_bytes(a))).all())