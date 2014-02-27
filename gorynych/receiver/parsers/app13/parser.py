# encoding: utf-8

from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE
from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

from pbformat import MobileId_pb2, trackevent_pb2, trackinfo_pb2
from constants import FrameId
from chunk_reader import ChunkReader

import zlib


@implementer(IParseMessage)
class App13Parser(object):
    '''
    Common class for mobile application tracker and satellite tracker.
    '''

    def __init__(self):
        self.imei = None
        self.handlers = {
            FrameId.MOBILEID: self._imei_handler,
            FrameId.PATHCHUNK: self._path_handler,
            FrameId.TRACK_INFO: self._track_event_handler,
            # to be filled
        }
        self.track_events = {
            0: 'TRACK_STARTED',
            1: 'TRACK_ENDED'
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

    def _track_event_handler(self, msg):
        e = trackevent_pb2.TrackEvent()
        e.ParseFromString(msg)
        if e.event not in self.track_events:
            raise TypeError('Unknown event: {} of {}'.format(e.event, self.track_events))
        self.points.append({
            'ts': e.timestamp,
            'event': self.track_events[e.event],
            'track_id': e.id
        })

    def _parse_frame(self, frame_id, frame_msg):
        if frame_id not in self.handlers:
            raise ValueError('Unknown frame id')
        self.handlers[frame_id](frame_msg)

    def _parse_collection(self, msg):
        frames = self._split_to_frames(msg)
        for frame in frames:
            self._parse_frame(frame.id, frame.msg)

    def check_message_correctness(self, msg):
        return msg

    def get_response(self, msg):
        frames = self._split_to_frames(msg)
        result = []
        for frame in frames:
            if frame.id == FrameId.PATHCHUNK:
                reader = ChunkReader(frame.msg)
                response = Frame(
                    FrameId.PATHCHUNK_CONF, reader.make_response())
                result.append(response.serialize())
        return result

    def parse(self, msg):
        self.points = []
        self._parse_collection(msg)

        # if no imei encountered, raise error
        if not self.imei:
            raise ValueError('Orphan message; no imei found')

        for point in self.points:
            point['imei'] = self.imei

        response = self.points
        del self.points
        return response


@implementer(IParseMessage)
class PathMakerParser(object):

    def __init__(self):
        self.handlers = {
            FrameId.MOBILEID: self._imei_handler,
            FrameId.PATHCHUNK: self._path_handler,
            FrameId.PATHCHUNK_ZIPPED: self._compressed_path_handler,
            FrameId.TRACK_INFO: self._track_event_handler,
            # to be filled
        }
        self.track_events = {
            0: 'TRACK_STARTED',
            1: 'TRACK_ENDED'
        }

    def _imei_handler(self, msg):
        mob_id = MobileId_pb2.MobileId()
        mob_id.ParseFromString(msg)
        if not mob_id.HasField('imei'):
            raise ValueError("ID frame contains no imei")
        return dict(imei=mob_id.imei)

    def _path_handler(self, msg):
        reader = ChunkReader(msg)
        return [point for point in reader.unpack()]

    def _track_event_handler(self, msg):
        e = trackevent_pb2.TrackEvent()
        e.ParseFromString(msg)
        if e.event not in self.track_events:
            raise TypeError('Unknown event: {} of {}'.format(e.event, self.track_events))
        return {
            'ts': e.timestamp,
            'event': self.track_events[e.event],
            'track_id': e.id
        }

    def _compressed_path_handler(self, msg):
        return self._path_handler(zlib.decompress(msg))

    def parse(self, frame):
        if frame.id not in self.handlers:
            raise ValueError('Unknown frame id')
        return self.handlers[frame.id](frame.msg)

    def check_message_correctness(self, msg):
        return msg

    def get_response(self, frame):
        if frame.id in [FrameId.PATHCHUNK, FrameId.PATHCHUNK_ZIPPED]:
            reader = ChunkReader(frame.msg)
            response = Frame(
                FrameId.PATHCHUNK_CONF, reader.make_response())
            return response.serialize()


class Frame(object):

    def __init__(self, frame_id, frame_msg):
        self.id = frame_id
        self.msg = frame_msg

    def __repr__(self):
        return self.serialize().encode('string_escape')

    def serialize(self):
        return HEADER.pack(MAGIC_BYTE, self.id, len(self.msg)) + self.msg

    def __eq__(self, other):
        return self.id == other.id and self.msg == other.msg
