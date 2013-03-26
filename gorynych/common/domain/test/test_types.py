import unittest

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


if __name__ == '__main__':
    unittest.main()
