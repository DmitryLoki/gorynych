'''
Twisted protocols for message receiving.
'''
from twisted.internet import protocol
from twisted.protocols import basic
from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE, FrameId
from gorynych.receiver.parsers.app13.parser import Frame
from gorynych.receiver.parsers.app13.session import PathMakerSession

import logging
logging.basicConfig(filename='pmtracker_detailed.log',
                    format='%(levelname)s: %(asctime)s %(message)s',
                    level=logging.INFO)


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
        response = self.service.parser.get_response(datagram)
        self.transport.write(response, sender)
        self.service.handle_message(datagram, proto='UDP', client=sender,
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


class FrameReceivingProtocol(protocol.Protocol):
    """
    lineReceiver-like class, accumulates received data in buffer,
    then fires frameReceived, when an app13 frame can be extracted from buffer
    """

    def __init__(self, *args, **kwargs):
        self._buffer = ''
        self.reset()

    def reset(self):
        # override this method some session-like behaviour is desired
        pass

    def frameReceived(self, frame):
        # override this method to do something with received frame
        raise NotImplementedError

    def dataReceived(self, data):
        logging.info("DATA_RECEIVED: " + data.encode('string_escape'))
        self._buffer += data
        cursor = 0
        while True:
            if len(self._buffer) < HEADER.size:
                logging.info("BUFFER_LESS_THEN_HEADER: " + self._buffer.encode('string_escape'))
                break
            if cursor >= len(self._buffer):
                logging.info("CURSOR_MORE_THEN_BUFFER: " + self._buffer.encode('string_escape'))
                break
            try:
                magic, frame_id, payload_len = HEADER.unpack_from(self._buffer, cursor)
            except:
                self.reset()
                raise ValueError('Unrecognized header')
            if magic != MAGIC_BYTE:
                self.reset()
                raise ValueError('Magic byte mismatch')
            frame_len = payload_len + HEADER.size
            if len(self._buffer[cursor:]) < frame_len:  # keep accumulating
                logging.info("BUFFER_LESS_THEN_FRAMELEN: " + self._buffer.encode('string_escape'))
                break
            msg = self._buffer[cursor + HEADER.size: cursor + frame_len]
            cursor += frame_len
            frame = Frame(frame_id, msg)
            logging.info("FRAME_RECEIVED_CALLED: " + msg.encode('string_escape'))
            self.frameReceived(frame)
        self._buffer = self._buffer[cursor:]


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
        try:  # catch any parser's exception
            resp = self.factory.service.parser.get_response(frame)
            if resp:
                self.transport.write(resp)
            parsed = self.factory.service.parser.parse(frame)
        except Exception as e:
            logging.warning(e.message)
            logging.warning(frame.serialize().encode('string_escape'))
            return
        if frame.id == FrameId.MOBILEID:
            self.session.init(parsed)
        else:
            if self.session.is_valid():
                for item in parsed:
                    item.update(self.session.params)
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
