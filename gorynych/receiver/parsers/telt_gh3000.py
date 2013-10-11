# encoding: utf-8

import time
import struct
import datetime
import traceback
from twisted.python import log

from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

FORMAT = {
    'lat': 'latitude (decimal degree)',
    'lon': 'longitude (decimal degree)',
    'alt': 'altitude (meters)',
    'h_speed': 'speed (kilometers per hour)',
    'imei': 'unique 15-digit sequence',
    'ts': 'unix timestamp (seconds)'
}


@implementer(IParseMessage)
class TeltonikaGH3000UDP(object):

    def __init__(self):
        self.format = FORMAT

    def bytes2coord(self, four_bytes):
        result = struct.unpack('>f', four_bytes)[0]
        return float('%.6f' % result)

    def get_alt(self, two_bytes):
        return struct.unpack('>h', two_bytes)[0]

    # def get_angle(self, one_byte):
    #     return ord(one_byte) * 360. / 256.

    def get_speed(self, one_byte):
        return ord(one_byte)

    def parse_time(self, four_bytes):
        ts_hex = four_bytes.encode('hex')
        ts_bin = bin(int(ts_hex, base=16))
        ts_bin = ts_bin[4:]
        ts_int = int(ts_bin, base=2)
        td = datetime.timedelta(seconds=ts_int)
        tdd = self.starttime + td
        real_ts = int(time.mktime(tdd.timetuple()))
        return real_ts

    def bitlify(self, mask):
        hex_value = mask.encode('hex')
        bin_str = bin(int(hex_value, base=16))
        return '0' * (8 - len(bin_str[2:])) + bin_str[2:]

    def check_message_correctness(self, msg):
        if not msg:
            raise ValueError(str(self.errors))
        return msg

    def get_response(self, bytestring):
        # 0005 is package length and should stay the same
        # 0002 is package id. no matter what's it
        # 01 is packet type (without ACK).
        packet_id = bytestring[5]
        num_of_data = bytestring[-1]
        return ''.join(('0005000201'.decode('hex'), packet_id,
                        num_of_data))

    def parse(self, bytestring):
        raw = bytestring
        self.starttime = datetime.datetime(2007, 1, 1, 0, 0)
        bytestring = bytestring[5:]

        self.packet_id = bytestring[0]
        # cutting if off too
        bytestring = bytestring[1:]

        imei = bytestring[2: 17]
        data = bytestring[17:]
        # codec_id = data[0]
        self.num_of_data = ord(data[1])

        # strip nums from the end and begining
        data = data[2:-1]
        # datalen = len(data)

        gps_mask_map = {
            0: (8, self.bytes2coord, 'latlng'),  # latlog
            1: (2, self.get_alt, 'alt'),  # alt
            2: (1, None, None),  # (1, self.get_angle, 'angle'),
            3: (1, self.get_speed, 'h_speed'),
            4: (1, None, None),
            5: (4, None, None),
            6: (1, None, None),
            7: (4, None, None)

        }

        io_map = {
            '01'.decode('hex'): 1,  # battery
            '02'.decode('hex'): 1,
            '05'.decode('hex'): 4,
            '14'.decode('hex'): 2,
            '15'.decode('hex'): 2,
            '16'.decode('hex'): 2,
            '43'.decode('hex'): 2,
            'DC'.decode('hex'): 4,
            'DD'.decode('hex'): 1,
            'DE'.decode('hex'): 1,
            'F0'.decode('hex'): 1,
            'F4'.decode('hex'): 1
        }

        records = []

        def read_gps(segment, mask):
            gpsdata = {}
            cursor2 = 0
            for idx, bit in enumerate(mask[::-1]):
                if bit == '1':
                    step, func, argname = gps_mask_map[idx]
                    if idx == 0:
                        gpsdata['lat'] = self.bytes2coord(
                            segment[cursor2: cursor2 + step / 2])
                        gpsdata['lon'] = self.bytes2coord(
                            segment[cursor2 + step / 2: cursor2 + step])
                    else:
                        if func:
                            gpsdata[argname] = func(
                                segment[cursor2: cursor2 + step])
                    cursor2 = cursor2 + step
            return gpsdata

        record_counter = 0  # incrementing at each record pass, no matter successful or not
        # required to prevent endless loops on bad data

        # for further logging
        self.errors = []

        cursor = 0
        while cursor < len(data) and record_counter <= self.num_of_data:
            try:
                # each loop pass is reading one record
                # it always starts with 4 bytes of time
                record = {
                    'imei': imei,
                    'ts': self.parse_time(data[cursor: cursor + 4]),
                }

                # then global mask
                gmask = self.bitlify(data[cursor + 4])
                # move cursor
                cursor = cursor + 5
                # then looking at global mask we'll find whats ahead
                for idx, bit in enumerate(gmask[::-1]):
                    if bit == '1':
                        # read the next segment. we are particulary interested in
                        # gps
                        if idx == 0:  # gps
                            gps_mask = self.bitlify(data[cursor])
                            gps_len = 0
                            for i, bit in enumerate(gps_mask[::-1]):
                                if bit == '1':
                                    gps_len += gps_mask_map[i][0]
                            gpsdata = read_gps(
                                data[cursor + 1: cursor + gps_len + 1], gps_mask)
                            record.update(gpsdata)
                            cursor = cursor + gps_len + 1
                        else:  # some other element. screw it for now, lets only find its length
                            # read the next field, it'll tell you how many key-value
                            # pairs in the segment
                            quantity = ord(data[cursor])

                            iocursor = cursor + 1
                            for io_element in xrange(quantity):
                                io_id = data[iocursor]

                                # check if it's a battery
                                if io_id == '01'.decode('hex'):
                                    record['battery'] = ord(data[iocursor + io_map[io_id]])

                                iocursor += io_map[io_id] + 1

                            cursor = iocursor
                            # now skip this element

                if  set(self.format.keys()).issubset(set(record.keys())):
                #if set(record.keys()).issubset(set(self.format.keys())):
                    records.append(record)
                record_counter += 1

            except:
                record_counter += 1
                self.errors.append(traceback.format_exc())
                continue

        if not records:
            log.err('Unparsed message %s' % raw)
        return records