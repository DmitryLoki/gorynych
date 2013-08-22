import unittest
import types

import mock

from gorynych.processor.domain import racetypes


class CheckpointAdapter(object):
    def __init__(self, chp, error_margin):
        self._point_inside = False
        self.checkpoint = chp
        self.error_margin = error_margin


def create_checkpoint_adapter(lat=40.1, lon=40.2, error_margin=50,
        radius=100):
    chp = mock.Mock()
    chp.lat, chp.lon, chp.radius = lat, lon, radius

    result = CheckpointAdapter(chp, error_margin)
    return result


class TestTakenOnExit(unittest.TestCase):
    def setUp(self):
        adapter = create_checkpoint_adapter()
        adapter.taken = types.MethodType(racetypes.taken_on_exit,
            adapter, CheckpointAdapter)
        self.adapter = adapter

    def tearDown(self):
        del self.adapter

    def test_point_outside(self):
        result = self.adapter.taken(41, 41, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertFalse(result)

    def test_point_inside(self):
        result = self.adapter.taken(40.1, 40.2, 15)
        self.assertTrue(self.adapter._point_inside)
        self.assertEqual(self.adapter.take_time, 15)
        self.assertFalse(result)

    def test_point_still_inside(self):
        self.adapter._point_inside = True
        result = self.adapter.taken(40.1, 40.2, 15)
        self.assertTrue(self.adapter._point_inside)
        self.assertEqual(self.adapter.take_time, 15)
        self.assertFalse(result)

    def test_point_outside_again(self):
        self.adapter._point_inside = True
        result = self.adapter.taken(41, 42, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertRaises(AttributeError, getattr, self.adapter, 'take_time')
        self.assertTrue(result)


class TestTakenOnEnter(unittest.TestCase):
    def setUp(self):
        adapter = create_checkpoint_adapter()
        adapter.taken = types.MethodType(racetypes.taken_on_enter,
            adapter, CheckpointAdapter)
        self.adapter = adapter

    def tearDown(self):
        del self.adapter

    def test_point_outside(self):
        result = self.adapter.taken(41, 41, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertFalse(result)

    def test_point_taken(self):
        result = self.adapter.taken(40.1, 40.2, 15)
        self.assertFalse(self.adapter._point_inside)
        self.assertTrue(result)
        self.assertEqual(self.adapter.take_time, 15)


class TestRaceTypesFactoryCreate(unittest.TestCase):
    def setUp(self):
        factory = racetypes.RaceTypesFactory()
        self.checkpoint_factory = mock.patch(
            'gorynych.processor.domain'
            '.racetypes.checkpoint_collection_from_geojson')
        self.checkpoint_factory.start()
        self.services = mock.patch(
            'gorynych.processor.domain.services.JavaScriptShortWay')
        self.services.start()
        self.factory = factory

    def tearDown(self):
        self.checkpoint_factory.stop()
        self.services.stop()

    def test_no_race_type(self):
        rtask = dict(rac_type='racetogoal')
        self.assertRaises(ValueError, self.factory.create, 'online', rtask)

    def test_no_race(self):
        rtask = dict(race_type='unknown')
        self.assertRaises(ValueError, self.factory.create, 'online', rtask)


if __name__ == '__main__':
    unittest.main()
