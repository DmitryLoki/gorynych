from operator import xor
import datetime
import time
import struct
import traceback

from zope.interface import Interface, implementer
from functools import reduce

from twisted.python import log

FORMAT = {
    'lat': 'latitude (decimal degree)',
    'lon': 'longitude (decimal degree)',
    'alt': 'altitude (meters)',
    'h_speed': 'speed (kilometers per hour)',
    'imei': 'unique 15-digit sequence',
    'ts': 'unix timestamp (seconds)'
}

MIN_SATTELITE_NUMBER = 2
MAXIMUM_HDOP = 10


class IParseMessage(Interface):

    '''
    I parse incoming messages from gps-trackers.
    '''
    def check_message_correctness(msg):
        '''
        I check is message correct by checking it's checksum or another
        method.
        @param msg: message from tracker.
        @type msg:
        @return: message from tracker if it was correct.
        @rtype: bytes
        @raise ValueError if message is incorrect.
        '''

    def parse(msg):
        '''
        I do the work.
        @param msg: message from device.
        @type msg:
        @return: parsed message.
        @rtype: dict
        '''


@implementer(IParseMessage)
class LogOnlyGlobalSatTR203(object):

    def __init__(self):
        self.format = dict(type=0, imei=1, lat=10, lon=9, alt=11,
                           h_speed=12, battery=16)
        self.convert = dict(type=str, imei=str, lat=self.latitude,
                            lon=self.longitude, alt=int, h_speed=self.speed,
                            battery=str)

    def speed(self, speed):
        return round(float(speed) * 1.609, 1)

    def latitude(self, lat):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        DD_lat = lat[1:3]
        MM_lat = lat[3:5]
        SSSS_lat = float(lat[5:]) * 60
        if lat[:1] == "N":
            sign = ''
        else:
            sign = '-'
        return float(sign + str(int(DD_lat) + float(MM_lat) / 60 +
                                SSSS_lat / 3600)[:9])

    def longitude(self, lon):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        DD_lon = lon[1:4]
        MM_lon = lon[4:6]
        SSSS_lon = float(lon[6:]) * 60
        if lon[:1] == "E":
            sign = ''
        else:
            sign = '-'
        return float(sign + str(int(DD_lon) + float(MM_lon) / 60 +
                                SSSS_lon / 3600)[:9])

    def check_message_correctness(self, msg):
        try:
            # Check checksum of obtained message.
            msg = str(msg)
            nmea = map(ord, msg[:msg.index('*')])
            check = reduce(xor, nmea)
            received_checksum = msg[msg.index('*') + 1:msg.index('!')]
            if not check == int(received_checksum, 16):
                raise ValueError("Incorrect checksum")
            # Check message quality.
            if not self._message_is_good(msg):
                raise ValueError("Bad GPS data or message type.")
        except Exception as e:
            raise ValueError(str(e))
        return msg

    def parse(self, msg):
        arr = msg.split('*')[0].split(',')
        result = dict()
        for key in self.format.keys():
            result[key] = self.convert[key](arr[self.format[key]])
        result['ts'] = int(time.mktime(
            time.strptime(''.join((arr[7], arr[8])), '%d%m%y%H%M%S')))
        return result

    def _message_is_good(self, msg):
        arr = msg.split('*')[0].split(',')
        gsr = arr[0] == 'GSr'
        satellites_number = int(arr[14])
        hdop = float(arr[15])
        return gsr and satellites_number > MIN_SATTELITE_NUMBER and (
            hdop < MAXIMUM_HDOP)


@implementer(IParseMessage)
class GlobalSatTR203(object):

    def __init__(self):
        self.format = dict(type=0, imei=1, lon=5, lat=6, alt=7,
                           h_speed=8, battery=9)
        self.convert = dict(type=str, imei=str, lat=self.latitude,
                            lon=self.longitude, alt=int, h_speed=self.speed,
                            battery=str)

    def speed(self, speed):
        return round(float(speed) * 1.609, 1)

    def latitude(self, lat):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        data = float(lat[1:])
        if lat[0] == "N":
            return data
        else:
            return -data

    def longitude(self, lon):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        data = float(lon[1:])
        if lon[0] == "E":
            return data
        else:
            return -data

    def check_message_correctness(self, msg):
        try:
            # Check checksum of obtained message.
            msg = str(msg)
            nmea = map(ord, msg[:msg.index('*')])
            check = reduce(xor, nmea)
            received_checksum = msg[msg.index('*') + 1:msg.index('!')]
            if not check == int(received_checksum, 16):
                raise ValueError("Incorrect checksum")
            # Check message quality.
            if not self._message_is_good(msg):
                raise ValueError("Bad GPS data or message type.")
        except Exception as e:
            raise ValueError(str(e))
        return msg

    def parse(self, msg):
        arr = msg.split('*')[0].split(',')
        result = dict()
        print arr
        for key in self.format.keys():
            print key
            result[key] = self.convert[key](arr[self.format[key]])
        result['ts'] = int(time.mktime(
            time.strptime(''.join((arr[3], arr[4])), '%d%m%y%H%M%S')))
        return result

    def _message_is_good(self, msg):
        arr = msg.split('*')[0].split(',')
        gsr = arr[0]
        fix = arr[2]
        hdop = float(arr[15])
        return gsr == 'GSr' and fix == 3 and hdop < MAXIMUM_HDOP


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
