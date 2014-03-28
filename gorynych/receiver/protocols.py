'''
Twisted protocols for message receiving.
'''
from twisted.internet import protocol
from twisted.protocols import basic
from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE, FrameId
from gorynych.receiver.parsers.app13.parser import Frame
from gorynych.receiver.parsers.app13.session import PathMakerSession
from gorynych.receiver.parsers.app13.pbformat.frameconf_pb2 import FrameConf
from gorynych.receiver.parsers.sbd import unpack_sbd


class TR203ReceivingProtocol(basic.LineOnlyReceiver):
    '''
    TCP-receiving protocol for tr203.
    '''

    delimiter = b'!'

    def lineReceived(self, line):
        if line.startswith('OK\r\n'):
            line = line[4:]
        self.factory.service.handle_message(line + '!', proto='TCP')


class UDPTR203Protocol(protocol.DatagramProtocol):
    '''
    UDP-receiving protocol for tr203.
    '''

    def __init__(self, service):
         self.service = service

    def datagramReceived(self, datagram, sender):
        self.service.handle_message(datagram, proto='UDP')


class UDPTeltonikaGH3000Protocol(protocol.DatagramProtocol):
    '''
    UDP receiving protocol for Teltonika GH3000.
    '''

    def __init__(self, service):
         self.service = service

    def datagramReceived(self, datagram, sender):
        response = self.service.parser.get_response(datagram)
        self.transport.write(response, sender)
        self.service.handle_message(datagram, proto='UDP', client=sender)


class App13ProtobuffMobileProtocol(protocol.Protocol):
    """
    New mobile application protocol, is also used by a satellite modem.
    """

    def __init__(self, *args, **kwargs):
        self.frames_recieved = 0

    def confirm(self, data):
        # legacy confirmation
        resp_list = self.factory.service.parser.get_response(data)
        for response in resp_list:
            self.transport.write(response)

        # new-style confirmation
        frames = self.factory.service.parser._split_to_frames(data)
        for frame in frames:
            self.frames_recieved += 1
            conf = FrameConf()
            conf.frames_recieved = self.frames_recieved
            f = Frame(FrameId.FRAME_CONF, conf.SerializeToString())
            self.transport.write(f.serialize())

    def dataReceived(self, data):
        self.confirm(data)
        self.factory.service.handle_message(
            data, proto='TCP')


class FrameReceivingProtocol(protocol.Protocol):
    """
    lineReceiver-like class, accumulates received data in buffer,
    then fires frameReceived, when an app13 frame can be extracted from buffer
    """

    def __init__(self, *args, **kwargs):
        self.reset()

    def reset(self):
        # override this method some session-like behaviour is desired
        pass

    def frameReceived(self, frame):
        # override this method to do something with received frame
        raise NotImplementedError

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
                self.reset()
                raise ValueError('Unrecognized header')
            if magic != MAGIC_BYTE:
                self.reset()
                raise ValueError('Magic byte mismatch')
            frame_len = payload_len + HEADER.size
            if len(self._buffer[cursor:]) < frame_len:  # keep accumulating
                break
            msg = self._buffer[cursor + HEADER.size: cursor + frame_len]
            cursor += frame_len
            frame = Frame(frame_id, msg)
            self.frameReceived(frame)
        self._buffer = self._buffer[cursor:]


class PathMakerProtocol(FrameReceivingProtocol):
    """
    Hybrid tracker protocol.
    """

    def reset(self):
        self.session = PathMakerSession()  # let's start new session
        self._buffer = ''
        self.frames_recieved = 0

    def confirm(self, frame):
        # legacy confirmation
        # response = self.factory.service.parser.get_response(frame)
        # self.transport.write(response)

        # new-style confirmation
        self.frames_recieved += 1
        conf = FrameConf()
        conf.frames_recieved = self.frames_recieved
        f = Frame(FrameId.FRAME_CONF, conf.SerializeToString())
        print f.serialize().encode('string_escape')
        self.transport.write(f.serialize())

    def frameReceived(self, frame):
        # log'n'check
        print 'gotcha', frame.serialize().encode('string_escape')
        result = self.factory.service.check_message(frame.serialize(), proto='TCP')
        self.confirm(frame)
        print self.factory.service.parser
        parsed = self.factory.service.parser.parse(frame)
        if frame.id == FrameId.MOBILEID:
            self.session.init(parsed)
        else:
            if self.session.is_valid():
                if isinstance(parsed, list):
                    for item in parsed:
                        item.update(self.session.params)
                        print item
                else:
                    parsed.update(self.session.params)
                    print parsed
                result.addCallback(lambda _: self.factory.service.store_point(parsed))
            else:
                self.reset()
                raise ValueError('Bad session: {}'.format(self.session.params))


class PathMakerSBDProtocol(FrameReceivingProtocol):
    """
    It's actually the same PathMakerProtocol encapsulated in SBD package.
    There're a few differences - no confirmation sent, no session,
    each SBD package contaits imei.
    """

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
        result = self.factory.service.check_message(frame.serialize(), proto='TCP')
        parsed = self.factory.service.parser.parse(frame)
        for item in parsed:
            item['imei'] = self.imei
        result.addCallback(lambda _: self.factory.service.store_point(parsed))


class RedViewGT60Protocol(protocol.Protocol):

    def dataReceived(self, data):
        self.factory.service.handle_message(
            data, proto='TCP')


tr203_tcp_protocol = TR203ReceivingProtocol
tr203_udp_protocol = UDPTR203Protocol
telt_gh3000_udp_protocol = UDPTeltonikaGH3000Protocol
app13_tcp_protocol = PathMakerProtocol
gt60_tcp_protocol = RedViewGT60Protocol
pmtracker_tcp_protocol = PathMakerProtocol
pmtracker_sbd_tcp_protocol = PathMakerSBDProtocol
