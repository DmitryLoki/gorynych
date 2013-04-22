import unittest
import simplejson as json

from shapely.geometry import Point

from gorynych.common.domain import types

class TypesTest(unittest.TestCase):
    def test_name(self):
        name = types.Name('firsTname  ', '  laStname')
        self.assertEqual(name.short(), 'F. Lastname')
        self.assertEqual(name.full(), 'Firstname Lastname')
        self.assertRaises(ValueError, types.Name)
        self.assertEqual(name.name, 'Firstname')
        self.assertEqual(name.surname, 'Lastname')


    def test_country(self):
        country = types.Country('mc123')
        self.assertEqual(country.code(), 'MC')
        self.assertRaises(ValueError, types.Country)


class AddressTest(unittest.TestCase):
    def test_success_creation(self):
        addr = types.Address('  ParIs', 'Fr', (1.08812, 3))
        self.assertEqual(addr.place, 'Paris')
        self.assertEqual(addr.country, 'FR')
        self.assertAlmostEqual(addr.lat, 1.08812, 6)
        self.assertAlmostEqual(addr.lon, 3, 6)

    def test_wrong_coordinates(self):
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (270, 0))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (0, 270))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (90, 0))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (-90, 0))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (-89,
                                                                  180.01))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (-89,
                                                                  -180.01))

    def test_coordinates(self):
        a1 = types.Address('ss', 'de', (-89.999999, -180))
        self.assertEqual(a1.coordinates, (-89.999999, -180))
        types.Address('ss', 'de', (-89.999999, 180))
        types.Address('ss', 'de', (89.999999, 180))
        types.Address('ss', 'de', (89.999999, -180))

    def test_country(self):
        a = types.Address('ss', 'de', (0,0))
        self.assertEqual(a.country, 'DE')

    def test_place(self):
        a = types.Address('ss', 'de', (0,0))
        self.assertEqual(a.place, 'Ss')


class CheckpointTest(unittest.TestCase):
    def test_creating(self):
        point1 = Point(42.502, 0.798)
        ch1 = types.Checkpoint(name='A01', geometry=point1,
                                ch_type='TO', times=(2, None), radius=2)
        ch2 = types.Checkpoint(name='A01', geometry=Point(42.502, 0.798),
                                 times=(4, 6), radius=3)
        ch3 = types.Checkpoint(name='B02', geometry=Point(1,2), ch_type='es',
            radius=3)
        ch4 = types.Checkpoint(name='g10', geometry={'type': 'Point',
                                                     'coordinates': [1, 2]},
            ch_type='goal', radius=3, times=(None, 8))

        self.assertEqual(ch1.geometry, point1)
        self.assertEqual(ch1.radius, 2)

        self.assertEqual(ch3.type, 'es')
        self.assertEqual(ch1.type, 'to')
        self.assertEqual(ch2.type, 'ordinal')

        self.assertIsNone(ch3.open_time)
        self.assertIsNone(ch3.close_time)

        self.assertEqual(ch4.name, 'G10')
        self.assertEqual(ch2.name, 'A01')

        self.assertIsInstance(ch4.geometry, Point)

    def test_geo_interface(self):
        ch1 = types.Checkpoint(name='A01', geometry=Point(53, 1),
                               ch_type='TO', times=(2, None), radius=2)
        expected_interface =  {'type': 'Feature',
                              'geometry': {'type': 'Point',
                                           'coordinates':[53.0, 1.0]},
                              'properties': {'radius': 2, 'name': 'A01',
                                            'checkpoint_type': 'to',
                                            'open_time': 2,
                                            'close_time': None}
                                }

        self.assertEqual(json.dumps(ch1.__geo_interface__),
                         json.dumps(expected_interface))

    def test_equal(self):
        ch1 = types.Checkpoint(name='A01', geometry=Point(53, 1),
                               ch_type='TO', times=(2, None), radius=2)
        ch2 = types.Checkpoint(name='A01', geometry=Point(53, 1),
                               ch_type='TO', times=(2, None), radius=2)
        self.assertEqual(ch1, ch2)
        ch3 = types.Checkpoint(name='A01', geometry=Point(53, 1),
                               ch_type='TO', times=(2, 3), radius=2)
        self.assertNotEqual(ch1, ch3)

    def test_checkpoint_from_geojson(self):
        point = {'geometry': {'type': 'Point', 'coordinates': [0.0, 1.0]},
                 'type': 'Feature',
                 'properties': {'name': "A01", 'radius': 400,
                              'open_time': 12345, 'close_time': 123456}}
        ch = types.checkpoint_from_geojson(point)
        self.assertIsInstance(ch, types.Checkpoint)
        self.assertEqual(ch.type, 'ordinal')
        self.assertDictContainsSubset(point['properties'],
                                      ch.__geo_interface__['properties'])
        self.assertIsInstance(ch.geometry, Point)

    def test_bad_creating(self):
        self.assertRaises(ValueError, types.Checkpoint, 'A01', Point(1,1))
        self.assertRaises(AssertionError, types.Checkpoint, '2', Point(2,2),
                                                           times=(3, 1),
                                                           radius=1)


if __name__ == '__main__':
    unittest.main()
