import unittest

from gorynych.common.domain import model

class IdentifierObjectTest(unittest.TestCase):
    def test_null(self):
        self.assertRaises(AttributeError, model.IdentifierObject, None)

    def test_int(self):
        int_id = model.IdentifierObject(1)
        self.assertEqual(1, int_id)

    def test_str(self):
        str_id = model.IdentifierObject('hello')
        self.assertEqual('hello', str_id)

    def test_identifier_object(self):
        id_1 = model.IdentifierObject('45')
        id_2 = model.IdentifierObject('45')
        self.assertEqual(id_1, id_2)

    def test_len(self):
        a = model.IdentifierObject('234')
        self.assertEqual(len(a), 3)


if __name__ == '__main__':
    unittest.main()
