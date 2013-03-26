import unittest

from shapely.geometry import Point

from gorynych.common.domain import types

class TypesTest(unittest.TestCase):
    def test_name(self):
        name = types.Name('firstname', 'lastname')
        self.assertEqual(name.short(), 'F. Lastname')
        self.assertEqual(name.full(), 'Firstname Lastname')
        self.assertRaises(ValueError, types.Name)

    def test_country(self):
        country = types.Country('mc')
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
        types.Address('ss', 'de', (-89.999999, -180))
        types.Address('ss', 'de', (-89.999999, 180))
        types.Address('ss', 'de', (89.999999, 180))
        types.Address('ss', 'de', (89.999999, -180))


class CheckpointTest(unittest.TestCase):
    def test_creating(self):
        point1 = Point(42.502, 0.798)
        ch1 = types.Checkpoint(name='A01', geometry=point1,
                                ch_type='TO', times=(2, None), radius=2)
        ch2 = types.Checkpoint(name='A01', geometry=Point(42.502, 0.798),
                                 times=(4, 6), radius=3)
        ch3 = types.Checkpoint(name='B02', geometry=Point(1,2), ch_type='es',
            radius=3)
        ch4 = types.Checkpoint(name='g10', geometry=Point(2,2),
            ch_type='goal', radius=3, times=(None, 8))

        self.assertEqual(ch1.geometry, point1)
        self.assertEqual(ch1.radius, 2)

        self.assertEqual(ch3.type, 'es')
        self.assertEqual(ch1.type, 'to')
        self.assertEqual(ch2.type, 'ordinal')

        self.assertIsNone(ch3.start_time)
        self.assertIsNone(ch3.end_time)

        self.assertEqual(ch4.name, 'G10')
        self.assertEqual(ch2.name, 'A01')

    def test_bad_creating(self):
        self.assertRaises(ValueError, types.Checkpoint, 'A01', Point(1,1))


if __name__ == '__main__':
    unittest.main()
