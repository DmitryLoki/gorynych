from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

import struct
import time
import datetime
from operator import xor


@implementer(IParseMessage)
class RedViewGT60(object):

    """
    The tracker's got two types of messages.

    1) A command - like login, confirm login, set some value etc.
            Commands are handled in handle_command method. It's empty since we
            don't need any commands for now. Commands begin from $$ (from tracker)
            or @@ (from server) and end with \r\n.

    2) A geodata piece.
            Contains lat, lng, timestamp and all that's useful. Handled in parse_geodata
            method. Geodata begins from a single $ and ends with #.

    ATTENTION: these two kinds of messages are not completely independent from each other.
    From GT60 protocol it seems that to be able to send geodata, a tracker needs to log in first.
    But practical examples so far demonstrates that login procedure can be ignored safely.
    Don't know if it's by the protocol or should I say thanks to our chinese friends. Just
    a memo.
    """

    precision = 6  # to round latlon coordinates

    def check_message_correctness(self, msg):
        checksum = ord(msg[-2])
        data = map(ord, msg[:-2])
        calculated_checksum = sum(data) % 256
        if checksum != calculated_checksum:
            raise ValueError("Incorrect checksum")
        return msg

    def parse(self, msg):
        # determine, whether msg a command or a piece of geodata.
        if msg[:1] == '$$' and msg[-2:] == '\r\n':
            return self.handle_command(msg)
        elif msg[0] == '$' and msg[-1] == '#':
            return self.parse_geodata(msg)
        else:
            raise ValueError('Unrecognized message type')

    def handle_command(self, msg):
        # nothing to do for now
        pass

    def parse_geodata(self, msg):
        points = []
        imei = str(int(msg[2:10].encode('hex'), 16))[:14]
        count = ord(msg[16])  # how many points are in the packet
        path = msg[17:-2]  # points here
        chunk_length = 16
        for i in xrange(count - 1):
            pathchunk = path[i * chunk_length: (i + 1) * chunk_length]
            point = dict(imei=imei,
                         lat=self.get_coord(pathchunk[0:4]),
                         lon=self.get_coord(pathchunk[4:8]),
                         ts=self.get_time(pathchunk[8:12]),
                         alt=int(pathchunk[12:14].encode('hex'), 16),
                         h_speed=0)
            points.append(point)
        print points
        return points

    def _to_int(self, bytestring):
        return struct.unpack('>i', bytestring)[0]

    def get_coord(self, bytestring):
        return round(self._to_int(bytestring)/60000., self.precision)

    def get_time(self, bytestring):
        offsets = [
            26,  # year
            22,  # month
            17,  # day
            12,  # hour
            6,   # min
            0,   # sec
        ]
        inttime = self._to_int(bytestring)
        timevalues = []
        for offset in offsets:
            value = inttime >> offset
            inttime = xor(inttime, value * 2 ** offset)
            timevalues.append(value)
        dt = datetime.datetime(*timevalues)
        return int(time.mktime(dt.timetuple()))
