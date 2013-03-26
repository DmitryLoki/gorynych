import unittest

from gorynych.info.domain import transport


def create_transport(id, type='bUs   ', title='   yELlow bus',
                     description=None):
    tr = transport.TransportFactory().create_transport(id, type, title,
                                                            description)
    return tr


class TransportFactoryTest(unittest.TestCase):

    def test_creation(self):
        trans = create_transport(transport.TransportID(15))
        self.assertEqual(trans.id, transport.TransportID(15))
        self.assertEqual(trans.type, 'bus')
        self.assertEqual(trans.title, 'Yellow bus')
        self.assertIsNone(trans.description)

        trans = create_transport(transport.TransportID(1), description='one')
        self.assertEqual(trans.id, transport.TransportID(1))
        self.assertEqual(trans.description, 'One')

    def test_incorrect_creation(self):
        self.assertRaises(ValueError, create_transport, 15, type='drdr')


if __name__ == '__main__':
    unittest.main()
