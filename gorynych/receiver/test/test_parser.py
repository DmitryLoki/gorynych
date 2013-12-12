'''
Tests for message parsers.
Then using this file subclass all test cases from ParserTest and put parser
instance in setUp method in a field self.parser.
'''
import unittest

from zope.interface.verify import verifyObject

from gorynych.receiver.parsers import IParseMessage, GlobalSatTR203, \
    TeltonikaGH3000UDP, RedViewGT60, App13Parser, PathMakerParser


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


class RedViewGT60TestCase(ParserTest):

    def setUp(self):
        self.parser = RedViewGT60()
        self.message = '$\x011\xed\xab\x95\xf8m\x8c*w\xfdU\x1c\x00\xa7\x05\x002\xfe\x05\x00"]\x836\x84\xb3\x91\x00\xe4\x00\x05\x002\xfe\x12\x00"]b6\x84\xb3\x9a\x00\xd4\x00\x00\x002\xfe\x12\x00"]b6\x84\xb3\x9f\x00\xd4\x00\x00\x002\xfe\x12\x00"]b6\x84\xb3\xa3\x00\xd4\x00\x00\x002\xfe\x12\x00"]b6\x84\xb3\xa8\x00\xd4\x00\x00a#'

    def test_parse(self):
        awaited = [
            {'lat': 55.69715, 'h_speed': 0, 'imei': '35977203379453',
                'alt': 228, 'lon': 37.53605, 'ts': 1380698057},
            {'lat': 55.697367, 'h_speed': 0, 'imei': '35977203379453',
                'alt': 212, 'lon': 37.5355, 'ts': 1380698066},
            {'lat': 55.697367, 'h_speed': 0, 'imei': '35977203379453',
                'alt': 212, 'lon': 37.5355, 'ts': 1380698071},
            {'lat': 55.697367, 'h_speed': 0, 'imei': '35977203379453',
                'alt': 212, 'lon': 37.5355, 'ts': 1380698075}]
        result = self.parser.parse(self.message)
        self.assertEqual(len(result), 4)
        for i, item in enumerate(result):
            self._check_values(
                item, h_speed=awaited[i]['h_speed'], lon=awaited[i]['lon'],
                lat=awaited[i]['lat'], imei=awaited[i]['imei'], alt=awaited[i]['alt'])

    def test_incorrect_message(self):
        bad_message = 'wtf?'
        self.assertRaises(ValueError, self.parser.parse, bad_message)

    def test_checksum(self):
        result = self.parser.check_message_correctness(self.message)
        self.assertEquals(result, self.message)

        bad_message = 'wtf again?'
        self.assertRaises(
            ValueError, self.parser.check_message_correctness, bad_message)


from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE, FrameId
from gorynych.receiver.parsers.app13.parser import Frame
import google.protobuf


class App13TestCase(ParserTest):

    def setUp(self):
        self.parser = App13Parser()
        self.message = '\xba\x01\x00&\n$3592b2dc-a9b2-4629-a9f8-e802d7cc870b\xba\x02\x00\xad\x10\xe3\xc2\x8d\x94\x05\x1d\x00\x0bQB%\x02\xc5\xe6@(\x000\xcb\xc0\xbb\xbf\x93\xc0\xeb\xbat@)H\x00R\t\n\x07n\x04\x11Q\xa4\x01\x00R\x08\n\x06n\x04\x07%H\x00R\x08\n\x06n\x04\t+V\x00R\x08\n\x06n\x04\r?|\x00R\x08\n\x06n\x04\x07#H\x00R\x08\n\x06n\x04\t/^\x00R\x08\n\x06n\x04\x07\x1f>\x00R\t\n\x07n\x04\x13U\xaa\x01\x00R\x08\n\x06n\x04\x0b7l\x00R\x08\n\x06n\x04\x07!B\x00R\x08\n\x06n\x04\t-\\\x00R\x08\n\x06n\x04\r9r\x00R\x08\n\x06n\x04\t/^\x00R\x07\n\x05j\x04-Z\x00'

    def test_parse(self):
        awaited = [
            {'v_speed': 0.0, 'h_speed': 41, 'lon': 7.211549, 'ts': 1384341859, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260742, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 82, 'lon': 7.210923, 'ts': 1384341861, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260605, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 36, 'lon': 7.211259, 'ts': 1384341863, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 43, 'lon': 7.211213, 'ts': 1384341865, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 62, 'lon': 7.211061, 'ts': 1384341867, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260635, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 36, 'lon': 7.211274, 'ts': 1384341869, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 47, 'lon': 7.211183, 'ts': 1384341871, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 31, 'lon': 7.211305, 'ts': 1384341873, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 85, 'lon': 7.210893, 'ts': 1384341875, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260589, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 54, 'lon': 7.211122, 'ts': 1384341877, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.26065, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 33, 'lon': 7.21129, 'ts': 1384341879, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 46, 'lon': 7.211198, 'ts': 1384341881, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 57, 'lon': 7.211106, 'ts': 1384341883, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260635, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 47, 'lon': 7.211183, 'ts': 1384341885, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 45, 'lon': 7.211198, 'ts': 1384341887, 'imei': u'3592b2dc-a9b2-4629-a9f8-e802d7cc870b', 'lat': 52.260666, 'alt': 0}]
        result = self.parser.parse(self.message)
        self.assertEqual(len(result), 15)
        for i, item in enumerate(result):
            self._check_values(
                item, h_speed=awaited[i]['h_speed'], lon=awaited[i]['lon'],
                lat=awaited[i]['lat'], imei=awaited[i]['imei'], alt=awaited[i]['alt'])

    def test_serialize(self):
        magic, frame_id, payload_len = HEADER.unpack_from(self.message, 0)
        self.assertEquals(magic, MAGIC_BYTE)
        self.assertEquals(frame_id, FrameId.MOBILEID)

    def test_response(self):
        response = self.parser.get_response(self.message)
        self.assertEqual(response, ['\xba\x04\x00\n\x08\xcb\xc0\xbb\xbf\x93\xc0\xeb\xbat'])
        magic, frame_id, payload_len = HEADER.unpack_from(response[0], 0)
        self.assertEquals(magic, MAGIC_BYTE)
        self.assertEquals(frame_id, FrameId.PATHCHUNK_CONF)

    def test_incorrect_message(self):
        bad_message = "slave to the new black gold, there's a heartbeat under my skin"
        self.assertRaises(
            ValueError, self.parser.parse, bad_message)  # magic byte mismatch

        # more tricky: set magic byte first
        self.assertRaises(
            ValueError, self.parser.parse, chr(MAGIC_BYTE) + bad_message)  # unknown frame_id

        # even more tricky: let's tamper with frame_id
        self.assertRaises(
            google.protobuf.message.DecodeError,
            self.parser.parse, chr(MAGIC_BYTE) + chr(FrameId.MOBILEID) + bad_message)


class PmtrackerTestCase(App13TestCase):

    """
    That parser actually runs with the same mechanics as App13Parser, but receives Frame object
    instead of str.
    """

    def setUp(self):
        self.parser = PathMakerParser()
        self.raw_message = '\xba\x02\x00\xad\x10\xe3\xc2\x8d\x94\x05\x1d\x00\x0bQB%\x02\xc5\xe6@(\x000\xcb\xc0\xbb\xbf\x93\xc0\xeb\xbat@)H\x00R\t\n\x07n\x04\x11Q\xa4\x01\x00R\x08\n\x06n\x04\x07%H\x00R\x08\n\x06n\x04\t+V\x00R\x08\n\x06n\x04\r?|\x00R\x08\n\x06n\x04\x07#H\x00R\x08\n\x06n\x04\t/^\x00R\x08\n\x06n\x04\x07\x1f>\x00R\t\n\x07n\x04\x13U\xaa\x01\x00R\x08\n\x06n\x04\x0b7l\x00R\x08\n\x06n\x04\x07!B\x00R\x08\n\x06n\x04\t-\\\x00R\x08\n\x06n\x04\r9r\x00R\x08\n\x06n\x04\t/^\x00R\x07\n\x05j\x04-Z\x00'
        magic, frame_id, payload_len = HEADER.unpack_from(self.raw_message, 0)
        msg = self.raw_message[HEADER.size: payload_len + HEADER.size]
        self.message = Frame(frame_id, msg)

    def test_parse(self):
        awaited = [
            {'v_speed': 0.0, 'h_speed': 41, 'lon': 7.211549, 'ts': 1384341859, 'lat': 52.260742, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 82, 'lon': 7.210923, 'ts': 1384341861, 'lat': 52.260605, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 36, 'lon': 7.211259, 'ts': 1384341863, 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 43, 'lon': 7.211213, 'ts': 1384341865, 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 62, 'lon': 7.211061, 'ts': 1384341867, 'lat': 52.260635, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 36, 'lon': 7.211274, 'ts': 1384341869, 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 47, 'lon': 7.211183, 'ts': 1384341871, 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 31, 'lon': 7.211305, 'ts': 1384341873, 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 85, 'lon': 7.210893, 'ts': 1384341875, 'lat': 52.260589, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 54, 'lon': 7.211122, 'ts': 1384341877, 'lat': 52.26065, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 33, 'lon': 7.21129, 'ts': 1384341879, 'lat': 52.260681, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 46, 'lon': 7.211198, 'ts': 1384341881, 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 57, 'lon': 7.211106, 'ts': 1384341883, 'lat': 52.260635, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 47, 'lon': 7.211183, 'ts': 1384341885, 'lat': 52.260666, 'alt': 0},
            {'v_speed': 0.0, 'h_speed': 45, 'lon': 7.211198, 'ts': 1384341887, 'lat': 52.260666, 'alt': 0}]

        result = self.parser.parse(self.message)
        self.assertEquals(result, awaited)

    def test_response(self):
        response = self.parser.get_response(self.message)
        self.assertEquals(response, '\xba\x04\x00\n\x08\xcb\xc0\xbb\xbf\x93\xc0\xeb\xbat')

    def test_incorrect_message(self):
        bad_frame = Frame(-1, 'you can fight like a krogan, run like a leopard')
        self.assertRaises(
            ValueError, self.parser.parse, bad_frame)
        bad_frame_normal_id = Frame(FrameId.MOBILEID, "but you'll never be better than Commander Shepard!")
        self.assertRaises(
            google.protobuf.message.DecodeError, self.parser.parse, bad_frame_normal_id)

from gorynych.receiver.parsers.sbd import unpack_sbd


class TestSbdParser(unittest.TestCase):
    # a little bit diffirent from any other
    def test_good_message(self):
        msg = '\x01\x00\xa4\x01\x00\x1c\x01\x02\x03\x0b300434060007200\x00\x00\x08\x00\x00R\xa8r\xce\x02\x00\x82\x03\x18\x95\x13\xd8\xfft\xe1TVY\x1bay\'\xd5\xd049\'\x8d\x0b\xfc\x06\xec\x0e2\x1e\x1aA\x1c\\l5l\xecLV"A\xec\\\xac6|\xfc,.`\x86\x94$\x9b\x0f\x98\xa1!\xcb\x91\x00Vd\xa6\xc8\x13\x04Q\xee\xa4,\x14`\x03fE\xa9\xcbx\x19\x05qr\xb1\xd7\xb1\xa4\xe9*\xb8i\x04\xb1q\xb1\xc8\x14\x18\xaa\x80%+\xcc\xd5\x8cD@"\x16\xce\x1a&`\x91"_%\x0bk0++X\xc5F\x04\x00\x8e\xd0\x1c]'
        expected = {
            'MOStatus': 0,
            'MTMSN': 0,
            'MOMSN': 8,
            'cdr': 16909067,
            'time': 1386771150,
            'imei': '300434060007200',
            'data': '\x03\x18\x95\x13\xd8\xfft\xe1TVY\x1bay\'\xd5\xd049\'\x8d\x0b\xfc\x06\xec\x0e2\x1e\x1aA\x1c\\l5l\xecLV"A\xec\\\xac6|\xfc,.`\x86\x94$\x9b\x0f\x98\xa1!\xcb\x91\x00Vd\xa6\xc8\x13\x04Q\xee\xa4,\x14`\x03fE\xa9\xcbx\x19\x05qr\xb1\xd7\xb1\xa4\xe9*\xb8i\x04\xb1q\xb1\xc8\x14\x18\xaa\x80%+\xcc\xd5\x8cD@"\x16\xce\x1a&`\x91"_%\x0bk0++X\xc5F\x04\x00\x8e\xd0\x1c]'
        }
        self.assertEquals(expected, unpack_sbd(msg))

    def test_bad_message(self):
        msg = "she'll be coming 'round the mountain when she comes"
        self.assertRaises(ValueError, unpack_sbd, msg)


if __name__ == '__main__':
    unittest.main()
