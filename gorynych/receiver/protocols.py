'''
Twisted protocols for message receiving.
'''
from struct import Struct

from twisted.internet import protocol
from twisted.protocols import basic

from gorynych.receiver.base_protocols import FrameReceivingProtocol


class TR203ReceivingProtocol(basic.LineOnlyReceiver):
    '''
    TCP-receiving protocol for tr203.
    '''

    delimiter = b'!'

    def lineReceived(self, line):
        if line.startswith('OK\r\n'):
            line = line[4:]
        self.factory.service.handle_message(line + '!', proto='TCP',
                                            device_type='tr203')


class UDPTR203Protocol(protocol.DatagramProtocol):
    '''
    UDP-receiving protocol for tr203.
    '''
    device_type = 'tr203'

    # def __init__(self, service):
    #     self.service = service

    def datagramReceived(self, datagram, sender):
        self.factory.service.handle_message(datagram, proto='UDP',
                                            device_type=self.device_type)


class UDPTeltonikaGH3000Protocol(protocol.DatagramProtocol):
    '''
    UDP receiving protocol for Teltonika GH3000.
    '''
    device_type = 'telt_gh3000'

    # def __init__(self, service):
    #     self.service = service

    def datagramReceived(self, datagram, sender):
        response = self.factory.service.parser.get_response(datagram)
        self.transport.write(response, sender)
        self.factory.service.handle_message(datagram, proto='UDP', client=sender,
                                            device_type=self.device_type)


class App13ProtobuffMobileProtocol(protocol.Protocol):
    """
    New mobile application protocol, is also used by a satellite modem.
    """
    device_type = 'app13'

    def dataReceived(self, data):
        resp_list = self.factory.service.parser.get_response(data)
        for response in resp_list:
            self.transport.write(response)
        self.factory.service.handle_message(
            data, proto='TCP', device_type=self.device_type)

from gorynych.receiver.parsers.app13.session import PathMakerSession
from gorynych.receiver.parsers.app13.parser import Frame
from gorynych.receiver.parsers.app13.constants import FrameId, MAGIC_BYTE


class PathMakerProtocol(FrameReceivingProtocol):
    """
    Hybrid tracker protocol.
    """
    device_type = 'pmtracker'

    def reset(self):
        self.session = PathMakerSession()  # let's start new session
        self._buffer = ''

    def frameReceived(self, frame):
        # log'n'check
        result = self.factory.service.check_message(frame.serialize(), proto='TCP',
                                                    device_type=self.device_type)
        resp = self.factory.service.parser.get_response(frame)
        if resp:
            self.transport.write(resp)
        parsed = self.factory.service.parser.parse(frame)
        if frame.id == FrameId.MOBILEID:
            self.session.init(parsed)
        else:
            if self.session.is_valid():
                for item in parsed:
                    item.update(self.session.params)
                print parsed
                result.addCallback(lambda _: self.factory.service.store_point(parsed))
            else:
                self.reset()
                raise ValueError('Bad session: {}'.format(self.session.params))

from gorynych.receiver.parsers.sbd import unpack_sbd


class PathMakerSBDProtocol(FrameReceivingProtocol):
    """
    It's actually the same PathMakerProtocol encapsulated in SBD package.
    There're a few differences - no confirmation sent, no session,
    each SBD package contaits imei.
    """
    device_type = 'pmtracker_sbd'

    def dataReceived(self, data):
        # override dataReceived to handle SBD and single-frame case
        msg = unpack_sbd(data)
        if not msg.get('imei') or not msg.get('data'):
            raise ValueError('Bad message (no imei or data): {}'.format(msg))
        self.imei = msg['imei']
        if ord(msg['data'][0]) != MAGIC_BYTE:
            # single-frame case
            frame = Frame(ord(msg['data'][0]), msg['data'][1:])
            self.frameReceived(frame)
        else:
            FrameReceivingProtocol.dataReceived(self, msg['data'])

    def frameReceived(self, frame):
        result = self.factory.service.check_message(frame.serialize(), proto='TCP',
                                                    device_type=self.device_type)
        parsed = self.factory.service.parser.parse(frame)
        for item in parsed:
            item['imei'] = self.imei
        print parsed
        result.addCallback(lambda _: self.factory.service.store_point(parsed))


class RedViewGT60Protocol(protocol.Protocol):
    device_type = 'gt60'

    def dataReceived(self, data):
        self.factory.service.handle_message(
            data, proto='TCP', device_type=self.device_type)


tr203_tcp_protocol = TR203ReceivingProtocol
tr203_udp_protocol = UDPTR203Protocol
telt_gh3000_udp_protocol = UDPTeltonikaGH3000Protocol
app13_tcp_protocol = App13ProtobuffMobileProtocol
gt60_tcp_protocol = RedViewGT60Protocol
pmtracker_tcp_protocol = PathMakerProtocol
pmtracker_sbd_tcp_protocol = PathMakerSBDProtocol
