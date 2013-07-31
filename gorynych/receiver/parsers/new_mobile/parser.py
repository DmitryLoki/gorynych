# encoding: utf-8

from struct import Struct

from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

from pbformat import MobileId_pb2
from constants import FrameId
from chunk_reader import ChunkReader


HEADER = Struct('!BBH')
MAGIC_BYTE = 0xBA


class Frame(object):

    def __init__(self, frame_id, frame_msg):
        self.id = frame_id
        self.msg = frame_msg

    def serialize(self):
        return HEADER.pack(MAGIC_BYTE, self.id, len(self.msg)) + self.msg


@implementer(IParseMessage)
class NewMobileTracker(object):

    def __init__(self):
        self.imei = None
        self.handlers = {
            FrameId.MOBILEID: self._imei_handler,
            FrameId.PATHCHUNK: self._path_handler,
            # to be filled
        }

    def _split_to_frames(self, raw):
        cursor = 0
        collection = []

        while True:
            if len(raw[cursor:]) < HEADER.size:
                break
            magic, frame_id, frame_len = HEADER.unpack_from(raw, cursor)

            if magic != MAGIC_BYTE:  # incredible fail
                raise ValueError('Magic byte mismatch')

            frame_start = cursor + HEADER.size
            frame_end = frame_start + frame_len
            msg = raw[frame_start:frame_end]
            collection.append(Frame(frame_id, msg))
            cursor += HEADER.size + frame_len

        return collection

    def _imei_handler(self, msg):
        mob_id = MobileId_pb2.MobileId()
        mob_id.ParseFromString(msg)
        if not mob_id.HasField('imei'):
            raise ValueError("ID frame contains no imei")
        self.imei = mob_id.imei

    def _path_handler(self, msg):
        reader = ChunkReader(msg)
        for point in reader.unpack():
            self.points.append(point)

    def parse(self, msg):
        frames = self._split_to_frames(msg)
        self.points = []
        for frame in frames:
            if frame.id not in self.handlers:
                raise ValueError('Unknown frame id')
            self.handlers[frame.id](frame.msg)

        # if no imei encountered, raise error
        if not self.imei:
            raise ValueError('Orphan message; no imei found')

        for point in self.points:
            point['imei'] = self.imei
            point['h_speed'] = 0

        response = self.points
        del self.points
        return response

    def check_message_correctness(self, msg):
        return msg

    def get_response(self, msg):
        frames = self._split_to_frames(msg)
        result = []
        for frame in frames:
            if frame.id == FrameId.PATHCHUNK:
                reader = ChunkReader(frame.msg)
                response = Frame(FrameId.PATHCHUNK_CONF, reader.make_response())
                result.append(response.serialize())
        return result
