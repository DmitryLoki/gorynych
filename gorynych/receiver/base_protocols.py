# base classes built on Twisted protocols for the purpose of good

from twisted.internet import protocol

from gorynych.receiver.parsers.app13.parser import Frame
from gorynych.receiver.parsers.app13.constants import HEADER, MAGIC_BYTE


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
            if len(self._buffer) < frame_len:  # keep accumulating
                break
            msg = self._buffer[cursor + HEADER.size: cursor + frame_len]
            cursor += frame_len
            frame = Frame(frame_id, msg)
            self.frameReceived(frame)
        self._buffer = self._buffer[cursor:]
