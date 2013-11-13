import unittest

from gorynych.receiver import factories


class TestReceivingFactory(unittest.TestCase):
    def test_init(self):
        factory = factories.ReceivingFactory('factory')
        self.assertEqual(factory.service, 'factory')
        self.assertIsNone(factory.protocol)


if __name__ == '__main__':
    unittest.main()
