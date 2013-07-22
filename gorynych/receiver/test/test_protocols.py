import mock

from twisted.trial.unittest import TestCase
from twisted.test.proto_helpers import FakeDatagramTransport
from twisted.internet.protocol import Factory

from gorynych.receiver.protocols import UDPTR203Protocol, UDPTeltonikaGH3000Protocol
from gorynych.receiver.receiver import ReceiverService


class MockFactory(Factory):
    pass


class ProtoTestCase(TestCase):

    def setUp(self):
        self.service = mock.Mock(spec=ReceiverService)
        telt_parser = mock.Mock()
        telt_parser.get_response.return_value = 'some response'
        self.service.parsers = {
            'telt_gh3000': telt_parser,
            'tr203': mock.Mock()
        }

        self.proto = self.protocol_type(self.service)
        self.transport = FakeDatagramTransport()
        self.proto.makeConnection(self.transport)
        self.transport.protocol = self.proto
        self.proto.factory = MockFactory()


class TestTR203(ProtoTestCase):
    protocol_type = UDPTR203Protocol

    def test_sat_datagramReceived(self):
        datagram = 'hello'
        addr = ('127.0.0.1', 10000)
        self.proto.datagramReceived(datagram, addr)
        self.service.handle_message.assert_called_with(datagram, proto='UDP', device_type='tr203')
        self.assertEquals(self.transport.written, [])


class TestTeltonicaGH3000(ProtoTestCase):
    protocol_type = UDPTeltonikaGH3000Protocol

    def test_teltonica_datagramReceived(self):
        datagram = 'hello'
        addr = ('127.0.0.1', 10000)
        self.proto.datagramReceived(datagram, addr)
        self.service.handle_message.assert_called_with(datagram, proto='UDP',
                                                       client=addr, device_type='telt_gh3000')
        self.assertEquals(self.transport.written, [
                          ('some response', ('127.0.0.1', 10000))])
