'''
Tests for message parsers.
Then using this file subclass all test cases from ParserTest and put parser
instance in setUp method in a field self.parser.
'''
import unittest

from zope.interface.verify import verifyObject

from gorynych.receiver.parsers import IParseMessage, GlobalSatTR203, \
    TeltonikaGH3000UDP


class ParserTest(unittest.TestCase):
    def test_parsed_interface(self):
        if hasattr(self, 'parser'):
            verifyObject(IParseMessage, self.parser)

    def _return_type_and_fields(self, result):
        self.assertIsInstance(result, dict)
        for item in ['lat', 'lon', 'imei', 'ts', 'alt']:
            self.assertIn(item, result.keys())

    def _check_values(self, result, **kwargs):
        self.assertDictContainsSubset(kwargs, result)


class GlobalSatTR203Test(ParserTest):
    def setUp(self):
        self.parser = GlobalSatTR203()

    def test_parse(self):
        message = 'GSr,011412001274897,3,3,00,,3,090713,081527,E02445.3853,N4239.2928,546,0.09,318,8,1.3,93,284,01,0e74,0f74,12,24*60!'
        result = self.parser.parse(message)
        print result
        self._return_type_and_fields(result)
        self._check_values(result, h_speed=0.1, battery='93', lon=24.756421,
            lat=42.65488, imei='011412001274897', alt=546)

    def test_correct_checksum(self):
        message = 'GSr,011412001415649,3,3,00,,3,090713,081447,E02445.3951,N4239.2872,536,0.27,28,5,7.2,93,284,01,0e74,0f74,12,27*54!'
        result = self.parser.check_message_correctness(message)
        self.assertEqual(message, result)

    def test_incorrect_checksum(self):
        message = 'GSr,011412001274897,3,3,00,,3,090713,081502,E02445.3855,N4239.2920,546,0.29,316,7,1.4,93,284,01,0e74,0f74,12,26*4f!'
        self.assertRaises(ValueError,
            self.parser.check_message_correctness, message)


class TeltonikaGH3000UDPTest(ParserTest):
    def setUp(self):
        self.parser = TeltonikaGH3000UDP


if __name__ == '__main__':
    unittest.main()
