'''
Tests for receiver service deployment.
'''
import unittest
from twisted.application.service import IServiceCollection

from zope.interface.verify import verifyObject

from gorynych.receiver import makeService, Options

DEFAULT_PORT = 9999

class TestMakeServiceErrors(unittest.TestCase):
    def test_missed_tracker_type(self):
        self.assertRaises(SystemExit, makeService, Options())

class _TCPTrackerMixin(unittest.TestCase):
    def test_tcp(self):
        if not hasattr(self, 'check_tcp'):
            pass
        else:
            self.check_tcp()


class _UDPTrackerMixin(unittest.TestCase):
    def test_udp(self):
        if not hasattr(self, 'check_udp'):
            pass
        else:
            self.check_udp()


class TestTrackerServices(unittest.TestCase):
    tracker = 'dumb_tracker'

    def setUp(self):
        self.options = Options()
        self.options['tracker'] = self.tracker
        self.service = makeService(self.options)
        self.sc = []
        for s in self.service:
            self.sc.append(s.name)

    def tearDown(self):
        del self.options
        del self.service
        del self.sc

    def _get_port(self, name):
        '''

        @param name: service name
        @type name: C{str}
        @return: method ('TCP' or 'UDP'), port number, factory or protocol (
        for UDP).
        @rtype: C{tuple}
        '''
        try:
            s = self.service.getServiceNamed(name)
        except KeyError:
            raise unittest.SkipTest("Can't get service %s" % name)
        return s.method, s.args[0], s.args[1]

    def test_return_interface(self):
        self.assertTrue(verifyObject(IServiceCollection, self.service))

    def check_udp(self):
        method, port, obj = self._get_port('_'.join((self.tracker, 'udp')))
        self.assertEqual('UDP', method)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual(self.udp_proto_class, obj.__class__.__name__)

    def check_tcp(self):
        method, port, obj = self._get_port('_'.join((self.tracker, 'tcp')))
        self.assertEqual('TCP', method)
        self.assertEqual(DEFAULT_PORT, port)
        self.assertEqual(self.tcp_proto_factory, obj.__class__.__name__)
        self.assertEqual(self.tcp_proto_class,
            obj.protocol().__class__.__name__)


class TestMakeService(TestTrackerServices):

    def test_collection_without_track(self):
        self.assertIn('ReceiverRabbitService', self.sc)
        self.assertIn('ReceiverService', self.sc)
        self.assertIn('WebLog', self.sc)
        self.assertEqual(len(self.sc), 3)


class TestMakeServiceTR203(TestTrackerServices, _TCPTrackerMixin,
    _UDPTrackerMixin):
    tracker = 'tr203'
    udp_proto_class = 'UDPTR203Protocol'
    tcp_proto_class = 'TR203ReceivingProtocol'
    tcp_proto_factory = 'TR203ReceivingFactory'


class TestMakeTeltonikaGH3000(TestTrackerServices, _UDPTrackerMixin):
    tracker = 'telt_gh3000'
    udp_proto_class = 'UDPTeltonikaGH3000Protocol'


class TestMakeApp13(TestTrackerServices, _TCPTrackerMixin):
    tracker = 'app13'
    tcp_proto_factory = 'App13ReceivingFactory'
    tcp_proto_class = 'App13ProtobuffMobileProtocol'


class TestMakeGT60(TestTrackerServices, _TCPTrackerMixin):
    tracker = 'gt60'
    tcp_proto_factory = 'GT60ReceivingFactory'
    tcp_proto_class = 'RedViewGT60Protocol'


if __name__ == '__main__':
    unittest.main()
