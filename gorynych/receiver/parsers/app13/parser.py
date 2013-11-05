# encoding: utf-8

from struct import Struct

from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

from pbformat import MobileId_pb2
from constants import FrameId
from chunk_reader import ChunkReader


class App13Parser(object):
    '''
    Common class for mobile application tracker and satellite tracker.
    '''
    HEADER = Struct('!BBH')
    MAGIC_BYTE = 0xBA

    def __init__(self):
        self.imei = None
        self.points = []
        self.handlers = {
            FrameId.MOBILEID: self._imei_handler,
            FrameId.PATHCHUNK: self._path_handler,
            # to be filled
        }

    def _imei_handler(self, msg):
        mob_id = MobileId_pb2.MobileId()
        mob_id.ParseFromString(msg)
        if not mob_id.HasField('imei'):
            raise ValueError("ID frame contains no imei")
        self.imei = mob_id.imei

    def _path_handler(self, msg):
        if not self.imei:
            raise ValueError('Unexpected path frame (session must be \
                initialized with ID frame first)')
        reader = ChunkReader(msg)
        for point in reader.unpack():
            point['imei'] = self.imei
            self.points.append(point)

    def parse_frame(self, frame):
        if frame.id not in self.handlers:
            raise ValueError('Unknown frame id')
        self.handlers[frame.id](frame.msg)

    def check_message_correctness(self, msg):
        return msg

    def get_response(self, frame):
        if frame.id == FrameId.PATHCHUNK:
            reader = ChunkReader(frame.msg)
            response = Frame(
                FrameId.PATHCHUNK_CONF, reader.make_response())
        return response

    def read(self):
        if not self.imei or not self.points:
            return []
        pts = self.points[:]
        self.points = []
        return pts


@implementer(IParseMessage)
class SBDParser(App13Parser):
    """
    Method 'parse' is a little bit different: simple-packed case is allowed,
    and message is a dict, not a string.
    """

    def parse(self, msg):
        # if no imei encountered, raise error
        if not msg['imei']:
            raise ValueError('Orphan message; no imei found')
        self.points = []

        if ord(msg['data'][0]) != self.MAGIC_BYTE:  # simple-packed frame, no collection
            self._parse_frame(ord(msg['data'][0]), msg['data'][1:])
        else:
            self._parse_collection(msg['data'])

        for point in self.points:
            point['imei'] = msg.imei

        response = self.points
        del self.points
        return response


class Frame(object):

    def __init__(self, frame_id, frame_msg):
        self.id = frame_id
        self.msg = frame_msg

    def __repr__(self):
        return self.serialize()

    def serialize(self):
        return App13Parser.HEADER.pack(App13Parser.MAGIC_BYTE, self.id, len(self.msg)) + self.msg
