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
        self.assertTrue('alt' in result)
        self.assertTrue('lat' in result)
        self.assertTrue('lon' in result)
        self.assertTrue('ts' in result)
        self.assertTrue('imei' in result)
        self.assertTrue('h_speed' in result)
        self.assertDictContainsSubset(kwargs, result)


class GlobalSatTR203Test(ParserTest):

    def setUp(self):
        self.parser = GlobalSatTR203()

    def test_parse(self):
        message = 'GSr,011412001275167,3,250713,212244,E024.705360,N42.648187,440,0,0.8,46*7e!'
        result = self.parser.parse(message)
        self._return_type_and_fields(result)
        self._check_values(result, h_speed=0, battery='46', lon=24.705360,
                           lat=42.648187, imei='011412001275167', alt=440)

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
        self.parser = TeltonikaGH3000UDP()
        self.message = "003c00000102000F313233343536373839303132333435070441bf9db00fff425adbd741ca6e1e009e1205070001030b160000601a02015e02000314006615000a160067010500000ce441bf9d920fff425adbb141ca6fc900a2b218070001030b160000601a02015e02000314006615000a160067010500000cc641bf9d740fff425adbee41ca739200b6c91e070001030b1f0000601a02015f02000314006615000a160066010500000ca841bf9cfc0fff425adba041ca70c100b93813070001030b1f0000601a02015f02000314002315000a160025010500000c3004".decode(
            'hex')

    def test_parse(self):
        awaited = [{'lat': 54.714687, 'h_speed': 5, 'imei': '123456789012345',
                    'alt': 158, 'lon': 25.303768, 'ts': 1196933760},
                   {'lat': 54.714542, 'h_speed': 24, 'imei': '123456789012345',
                       'alt': 162, 'lon': 25.304583, 'ts': 1196933730},
                   {'lat': 54.714775, 'h_speed': 30, 'imei': '123456789012345',
                       'alt': 182, 'lon': 25.306431, 'ts': 1196933700},
                   {'lat': 54.714478, 'h_speed': 19, 'imei': '123456789012345',
                       'alt': 185, 'lon': 25.305056, 'ts': 1196933580}]

        result = self.parser.parse(self.message)
        self.assertEqual(len(result), 4)
        for i, item in enumerate(result):
            self._check_values(
                item, h_speed=awaited[i]['h_speed'], lon=awaited[i]['lon'],
                lat=awaited[i]['lat'], imei=awaited[i]['imei'], alt=awaited[i]['alt'])

    def test_response(self):
        response = self.parser.get_response(self.message)
        self.assertEqual(response.encode('hex'), '00050002010204')

    def test_incorrect_message(self):
        message = '\nat+cgreg?\r\nat+csq\r\nGSr,011412001291453,3,3,00,,3,170713,114926,E02444.8435,N4239.2881,2276,12.99,40,7,1.1,81,284,01'
        self.assertEqual(self.parser.parse(message), [])

if __name__ == '__main__':
    unittest.main()
