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

if __name__ == '__main__':
    unittest.main()
