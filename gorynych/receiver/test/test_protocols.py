import mock

from twisted.trial import unittest
from twisted.test import proto_helpers

from gorynych.receiver.protocols import UDPTR203Protocol, UDPTeltonikaGH3000Protocol, \
    RedViewGT60Protocol, App13ProtobuffMobileProtocol, PathMakerProtocol, TR203ReceivingProtocol, \
    PathMakerSBDProtocol
from gorynych.receiver.receiver import ReceiverService
from gorynych.receiver.factories import ReceivingFactory


class BaseProtoTestCase(unittest.TestCase):
    """
    Base class for testing protocols.
    You need to define those in your subclass to work correctly:

     * protocol_type
     * transport_type ('udp' or 'tcp')
     * also if need to mock parser (f.e. to get responses), look up the next method
    """

    def setUp(self):
        self.service = mock.Mock(spec=ReceiverService)
        mockparser = mock.Mock()
        mockparser.get_response.return_value = 'some response'
        self.service.parser = mockparser
        self.proto = self.protocol_type()
        self.proto.factory = ReceivingFactory(self.service)
        if self.transport_type == 'tcp':
            self.tr = proto_helpers.StringTransport()
            self.proto.makeConnection(self.tr)
        elif self.transport_type == 'udp':
            self.tr = proto_helpers.FakeDatagramTransport()
        self.proto.transport = self.tr


class TestTR203_UDP(BaseProtoTestCase):
    protocol_type = UDPTR203Protocol
    transport_type = 'udp'

    def test_datagramReceived(self):
        dgram = 'hello'
        addr = ('127.0.0.1', 10000)
        self.proto.datagramReceived(dgram, addr)
        self.service.handle_message.assert_called_with(dgram, proto='UDP',
                                                       device_type='tr203')
        self.assertEquals(self.tr.written, [])


class TestTR203_TCP(BaseProtoTestCase):
    protocol_type = TR203ReceivingProtocol
    transport_type = 'tcp'

    def test_lineReceived(self):
        data = 'hello'
        self.proto.lineReceived(data)
        # exclamation mark is a delimiter
        self.service.handle_message.assert_called_with(data + '!', proto='TCP',
                                                       device_type='tr203')
        self.assertEquals(self.tr.value(), '')


class TestTeltonicaGH3000_UDP(BaseProtoTestCase):
    protocol_type = UDPTeltonikaGH3000Protocol
    transport_type = 'udp'

    def test_datagramReceived(self):
        dgram = 'hello'
        addr = ('127.0.0.1', 10000)
        self.proto.datagramReceived(dgram, addr)
        self.service.handle_message.assert_called_with(dgram, proto='UDP',
                                                       client=addr,
                                                       device_type='telt_gh3000')
        self.assertEquals(self.tr.written, [
                          ('some response', ('127.0.0.1', 10000))])


class TestRedViewGT60_TCP(BaseProtoTestCase):
    protocol_type = RedViewGT60Protocol
    transport_type = 'tcp'

    def test_dataReceived(self):
        data = 'hello'
        self.proto.dataReceived(data)
        self.service.handle_message.assert_called_with(data, proto='TCP',
                                                       device_type='gt60')
        self.assertEquals(self.tr.value(), '')


class TestApp13_TCP(BaseProtoTestCase):
    protocol_type = App13ProtobuffMobileProtocol
    transport_type = 'tcp'

    def test_dataReceived(self):
        data = 'hello'
        self.proto.dataReceived(data)
        self.service.handle_message.assert_called_with(data, proto='TCP',
                                                       device_type='app13')
        self.assertEquals(self.tr.value(), 'some response')


from gorynych.receiver.parsers.app13.parser import Frame
from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE, FrameId


class TestPathMaker_TCP(BaseProtoTestCase):
    """
    This test is *different*. PathMaker protocols contains quite a lot of logic,
    so we drop data into carefully, with portions, check consistency and bad pieces.
    It also contains session: check its work too.
    """
    protocol_type = PathMakerProtocol
    transport_type = 'tcp'

    def test_bad_dataReceived(self):
        self.assertRaises(ValueError, self.proto.dataReceived, 'hello')

    def test_good_data_no_session(self):
        # sends data without any session initialized. Should raise exception
        msg = 'kill all humans!'
        data = HEADER.pack(MAGIC_BYTE, FrameId.PATHCHUNK, len(msg)) + msg
        self.assertRaises(ValueError, self.proto.dataReceived, data)

    def test_init_session_with_bad_data(self):
        msg = 'ok, ok, HELLO'
        data = HEADER.pack(MAGIC_BYTE, FrameId.MOBILEID, len(msg)) + msg
        self.proto.dataReceived(data)
        self.assertFalse(self.proto.session.is_valid())

    def test_init_session_with_good_data(self):
        msg = 'maybe kill all humans again?'
        self.service.parser.parse.return_value = {'imei': 'Bender Bending Rodriguez'}
        data = HEADER.pack(MAGIC_BYTE, FrameId.MOBILEID, len(msg)) + msg
        self.proto.dataReceived(data)
        self.assertTrue(self.proto.session.is_valid())

    def test_send_message_to_receiver(self):
        # session first
        msg = 'good news, everyone!'
        self.service.parser.parse.return_value = {'imei': 'Hubert Farnsworth'}
        data = HEADER.pack(MAGIC_BYTE, FrameId.MOBILEID, len(msg)) + msg
        self.proto.dataReceived(data)

        # then data
        self.service.parser.parse.return_value = [{'some_param': 'some_data'}]
        data = HEADER.pack(MAGIC_BYTE, FrameId.PATHCHUNK, len(msg)) + msg
        self.proto.dataReceived(data)
        calls = self.service.check_message.mock_calls
        self.assertEquals(len(calls), 3)  # two times 'good news' plus one store_point
        # need to check actually that self.service.store_point was called, but dunno
        # how to do it. Think and try again later

    def test_send_message_by_letter(self):
        msg = 'Pizza_delivery'
        self.service.parser.parse.return_value = {'imei': 'Phillip J. Fry'}
        data = HEADER.pack(MAGIC_BYTE, FrameId.MOBILEID, len(msg)) + msg
        for letter in data[:-1]:
            self.proto.dataReceived(letter)
            self.assertFalse(self.proto.session.is_valid())
        self.proto.dataReceived(data[-1])
        self.assertTrue(self.proto.session.is_valid())


class TestPathMakerSBD_TCP(BaseProtoTestCase):
    protocol_type = PathMakerSBDProtocol
    transport_type = 'tcp'

    def setUp(self):
        super(TestPathMakerSBD_TCP, self).setUp()
        self.proto.frameReceived = mock.MagicMock()

    def test_send_sbd_message(self):
        # SBD protocols contain two parsers, so need to send actual message
        msg = '\x01\x00\xa3\x01\x00\x1c\x01\x02\x03\x08300434060007200\x00\x00\x05\x00\x00R\xa8r\xa1\x02\x00\x81\x03\x18\x95\x13\x98\xf4t\xe1TV\xd9\x93\x82\xf2N\xaa\x9cYrN\x1ao\xf8\rX\x1cD=\x84\x83\xd8\xb9Xm\xd8\xb8\x19=\x82\xd8\xb8X,x\x99y\xc0\x02\\\xa2\xac\x1a`\x86\x804\xbb\t\x98!\xa1\xcci\x01f\xc8ir\x1b\x05qp\xb1\xd5\xa8\x98\xf2;\xa9\x83\x84btl\x05\xc1\xe6\xe4\x98y\xfa0\x80\xe5l\x02y-\xc0\x06\xe4\xb8\x84\xdb0\x80\x8c\xd6\xf1Kt\x03K\x85\xa5\xf3\xdb@T\'\x14\xfb0\x00\x00-\x9b\x1a\xc1'
        expected = Frame(FrameId.PATHCHUNK_ZIPPED, '\x18\x95\x13\x98\xf4t\xe1TV\xd9\x93\x82\xf2N\xaa\x9cYrN\x1ao\xf8\rX\x1cD=\x84\x83\xd8\xb9Xm\xd8\xb8\x19=\x82\xd8\xb8X,x\x99y\xc0\x02\\\xa2\xac\x1a`\x86\x804\xbb\t\x98!\xa1\xcci\x01f\xc8ir\x1b\x05qp\xb1\xd5\xa8\x98\xf2;\xa9\x83\x84btl\x05\xc1\xe6\xe4\x98y\xfa0\x80\xe5l\x02y-\xc0\x06\xe4\xb8\x84\xdb0\x80\x8c\xd6\xf1Kt\x03K\x85\xa5\xf3\xdb@T\'\x14\xfb0\x00\x00-\x9b\x1a\xc1')
        self.proto.dataReceived(msg)
        self.proto.frameReceived.assert_called_with(expected)
