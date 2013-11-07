'''
Twisted protocols for message receiving.
'''
from struct import Struct

from twisted.internet import protocol
from twisted.protocols import basic
from twisted.python import log
from twisted.web.resource import Resource

from gorynych.receiver.parsers.app13.parser import Frame
from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE, FrameId
from gorynych.receiver.parsers.app13.session import PathMakerSession


def check_device_type(msg):
    if msg[0] == 'G':
        result = 'tr203'
    else:
        result = 'telt_gh3000'
    return result


class UDPReceivingProtocol(protocol.DatagramProtocol):

    '''
    Unused.
    '''

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, addr):
        device_type = check_device_type(datagram)
        if device_type == 'telt_gh3000':
            response = self.service.parsers[device_type].get_response(datagram)
            self.transport.write(response, addr)
        self.service.handle_message(datagram, proto='UDP', client=addr,
                                    device_type=device_type)


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

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, sender):
        self.service.handle_message(datagram, proto='UDP',
                                    device_type=self.device_type)


class UDPTeltonikaGH3000Protocol(protocol.DatagramProtocol):

    '''
    UDP receiving protocol for Teltonika GH3000.
    '''
    device_type = 'telt_gh3000'

    def __init__(self, service):
        self.service = service

    def datagramReceived(self, datagram, sender):
        response = self.service.parsers[
            self.device_type].get_response(datagram)
        self.transport.write(response, sender)
        self.service.handle_message(datagram, proto='UDP', client=sender,
                                    device_type=self.device_type)


class MobileReceivingProtocol(protocol.Protocol):

    '''
    Protocol for old unused mobile application.
    '''
    device_type = 'mobile'

    def dataReceived(self, data):
        self.factory.service.handle_message(
            data, proto='TCP', device_type=self.device_type)


class App13ProtobuffMobileProtocol(protocol.Protocol):

    """
    New mobile application protocol, is also used by a satellite modem.
    """
    device_type = 'app13'

    def dataReceived(self, data):
        resp_list = self.factory.service.parsers[
            self.device_type].get_response(data)
        for response in resp_list:
            self.transport.write(response)
        self.factory.service.handle_message(
            data, proto='TCP', device_type=self.device_type)


class PathMakerProtocol(protocol.Protocol):

    """
    New mobile application protocol, is also used by a satellite modem.
    """
    device_type = 'pmtracker'

    def __init__(self, *args, **kwargs):
        self._reset()

    def _reset(self):
        self.session = PathMakerSession()  # let's start new session
        self._buffer = ''

    def dataReceived(self, data):
        self._buffer += data
        cursor = 0
        while True:
            if len(self._buffer) < HEADER.size:
                break
            if cursor >= len(self._buffer):
                break
            try:
                magic, frame_id, payload_len = HEADER.unpack_from(self._buffer, cursor)
            except:
                self._reset()
                raise ValueError('Unrecognized header')
            if magic != MAGIC_BYTE:
                self._reset()
                raise ValueError('Magic byte mismatch')
            frame_len = payload_len + HEADER.size
            if len(self._buffer) < frame_len:  # keep accumulating
                break
            msg = self._buffer[cursor+HEADER.size: cursor+frame_len]
            cursor += frame_len

            # go to the parser
            result = self.factory.service.check_message(data, proto='TCP',
                                                        device_type=self.device_type)
            data = Frame(frame_id, msg)
            resp = self.factory.service.parsers[self.device_type].get_response(data)
            if resp:
                self.transport.write(resp)
            parsed = self.factory.service.parsers[self.device_type].parse(data)

            if frame_id == FrameId.MOBILEID:
                self.session.init(parsed)
            else:
                if self.session.is_valid():
                    for item in parsed:
                        item.update(self.session.params)
                    result.addCallback(lambda _: self.factory.service.store_point(parsed))
                else:
                    self._reset()
                    raise ValueError('Bad session: {}'.format(self.session.params))

        self._buffer = self._buffer[cursor:]


class IridiumSBDProtocol(protocol.Protocol):

    """
    It's actually the same App13ProtobuffMobileProtocol encapsulated in SBD package.
    It also sends no confirmation.
    """
    device_type = 'new_mobile_sbd'

    def __init__(self):
        self.main_struct = Struct('!BH')
        self.element_struct = Struct('!I15sBHHI')

    def _unpack_sbd(self, data):
        msg = dict()

        def parce_element(data, iei, cursor, size):
            if iei == 1:  # header
                msg['cdr'], msg['imei'], msg['MOStatus'], msg['MOMSN'],\
                    msg['MTMSN'], msg['time'] = \
                    self.element_struct.unpack_from(data, cursor)
            elif iei == 2:  # message
                msg['data'] = data[cursor:cursor + size]

        protocol_revision, total = self.main_struct.unpack_from(data)
        total += 3
        cursor = 3
        assert len(data) == total
        while cursor < total:
            iei, size = self.main_struct.unpack_from(data, cursor)
            cursor += 3
            parce_element(data, iei, cursor, size)
            cursor += size
        return msg

    def dataRaceived(self, data):
        msg = self._unpack_sbd(data)
        self.factory.service.handle_message(
            msg, proto='TCP', device_type=self.device_type)


class HttpTR203Resource(Resource):
    isLeaf = True
    device_type = 'tr203'

    def __init__(self, service):
        Resource.__init__(self)
        self.service = service

    def _handle(self, msg):
        self.service.handle_message(msg, proto='HTTP',
                                    device_type=self.device_type)
        return 'OK'

    def render_GET(self, msg):
        log.msg('GET: {}, args: {}'.format(msg, msg.args))
        return self._handle(msg.content.read())

    def render_POST(self, msg):
        log.msg('POST: {}, args: {}'.format(msg, msg.args))
        return self._handle(msg.content.read())


class RedViewGT60Protocol(protocol.Protocol):
    device_type = 'gt60'

    def dataReceived(self, data):
        self.factory.service.handle_message(
            data, proto='TCP', device_type=self.device_type)
