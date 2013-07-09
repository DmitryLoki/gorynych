import unittest
import mock

from gorynych.receiver.protocols import UDPReceivingProtocol

class TestUDPReceivingProtocol(unittest.TestCase):
    def test_datagramReceived(self):
        s = mock.Mock()
        p = UDPReceivingProtocol(s)
        datagram = 'hello'
        addr = 'world'
        p.datagramReceived(datagram, addr)
        s.handle_message.assert_called_with(datagram, proto='UDP',
            client=addr)


if __name__ == '__main__':
    unittest.main()
