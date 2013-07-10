from operator import xor
import time
import datetime

from zope.interface import Interface, implementer


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
class GlobalSatTR203(object):

    def __init__(self):
        self.format = dict(type = 0, imei = 1, lat = 10, lon = 9, alt = 11,
            h_speed = 12, battery = 16)
        self.convert = dict(type = str, imei = str, lat = self.latitude,
            lon = self.longitude, alt = int, h_speed = self.speed,
            battery = str)

    def speed(self, speed):
        return round(float(speed) * 1.609, 1)

    def latitude(self, lat):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        DD_lat = lat[1:3]
        MM_lat = lat[3:5]
        SSSS_lat = float(lat[5:])*60
        if lat[:1] == "N":
            sign = ''
        else:
            sign = '-'
        return float(sign + str(int(DD_lat) + float(MM_lat)/60 +
                                SSSS_lat/3600)[:9])

    def longitude(self, lon):
        """
        Convert gps coordinates from GlobalSat tr203 to decimal degrees format.
        """
        DD_lon = lon[1:4]
        MM_lon = lon[4:6]
        SSSS_lon = float(lon[6:])*60
        if lon[:1] == "E":
            sign = ''
        else:
            sign = '-'
        return float(sign + str(int(DD_lon) + float(MM_lon)/60 +
                                SSSS_lon/3600)[:9])

    def check_message_correctness(self, msg):
        """Check checksum of obtained msg."""
        try:
            msg = str(msg)
            nmea = map(ord, msg[:msg.index('*')])
            check = reduce(xor, nmea)
            received_checksum = msg[msg.index('*')+1:msg.index('!')]
            if check == int(received_checksum, 16):
                return msg
            else:
                raise ValueError("Incorrect checksum")
        except Exception as e:
            raise ValueError(str(e))

    def parse(self, msg):
        arr = msg.split('*')[0].split(',')
        if arr[0] == 'GSr':
            result = dict()
            for key in self.format.keys():
                result[key] = self.convert[key](arr[self.format[key]])
            result['ts'] = int(time.mktime(
                time.strptime(''.join((arr[7], arr[8])),'%d%m%y%H%M%S')))
            return result


@implementer(IParseMessage)
class TeltonikaGH3000UDP(object):

    def check_message_correctness(self, msg):
        return msg

    def get_response(self, bytestring):
        packet_id = bytestring[0]
        num_of_data = ord(bytestring[1])
        response = ''.join(('0005000201'.decode('hex'), packet_id,
                            chr(num_of_data)))
        return response

    def parse(self, bytestring):

        def bytes2coord(four_bytes):
            hex_data = four_bytes.encode('hex')
            c = int(hex_data, 16)
            return (c & 0x7fffff | 0x800000) * 1.0 / 2**23 * 2**((c>>23 & 0xff) - 127)

        def get_alt(two_bytes):
            return int(two_bytes.encode('hex'), 16)

        def get_angle(one_byte):
            return ord(one_byte) * 360. / 256.

        def get_speed(one_byte):
            return ord(one_byte)

        def parse_time(four_bytes):
            ts_hex = four_bytes.encode('hex')
            ts_bin = bin(int(ts_hex, base=16))
            ts_bin = ts_bin[3:]
            ts_int = int(ts_bin, base=2)
            td = datetime.timedelta(seconds=ts_int)
            tdd = starttime + td
            real_ts = int(time.mktime(tdd.timetuple()))
            return real_ts

        def bitlify(mask):
            hex_value = mask.encode('hex')
            bin_str = bin(int(hex_value, base=16))
            return '0' * (8 - len(bin_str[2:])) + bin_str[2:]

        bytestring = bytestring[5:]

        avl_id = bytestring[0]
        # cutting if off too
        bytestring = bytestring[1:]

        imei = bytestring[2: 17]
        data = bytestring[17:]
        codec_id = data[0]
        num_of_data = ord(data[1])

        # strip nums from the end and begining
        data = data[2:-1]
        datalen = len(data)

        starttime = datetime.datetime(2007, 1, 1, 0, 0)

        gps_mask_map = {
            0: (8, bytes2coord, 'latlng'),  # latlog
            1: (2, get_alt, 'alt'),  # alt
            2: (1, get_angle, 'angle'),  #
            3: (1, get_speed, 'h_speed'),
            4: (1, None, None),
            5: (4, None, None),
            6: (1, None, None),
            7: (4, None, None)

        }

        message = {'imei': imei}

        def read_gps(segment, mask):
            gpsdata = {}
            cursor2 = 0
            for idx, bit in enumerate(mask[::-1]):
                if bit == '1':
                    step, func, argname = gps_mask_map[idx]
                    if idx == 0:
                        gpsdata['lat'] = bytes2coord(segment[cursor2: cursor2 + step/2])
                        gpsdata['lon'] = bytes2coord(segment[cursor2 + step/2: cursor2 + step])
                    else:
                        if func:
                            gpsdata[argname] = func(segment[cursor2: cursor2+step])
                    cursor2 = cursor2 + step
            return gpsdata


        cursor = 0
        while cursor < len(data):
            # each loop pass is reading one record
            # it always starts with 4 bytes of time
            record = {
                'ts': parse_time(data[cursor: cursor+4]),
            }

            # then global mask
            gmask = bitlify(data[cursor+4])

            # move cursor
            cursor = cursor+4
            # then looking at global mask we'll find whats ahead
            for idx, bit in enumerate(gmask[::-1]):
                if bit == '1':

                    # read the next segment. we are particulary interested in gps
                    if idx == 0:  # gps
                        gps_mask = bitlify(data[cursor+1])
                        gps_len = 0
                        for i, bit in enumerate(gps_mask[::-1]):
                            if bit == '1':
                                gps_len += gps_mask_map[i][0]

                        gpsdata = read_gps(data[cursor+2: cursor+gps_len+2], gps_mask)
                        record.update(gpsdata)
                        cursor = cursor+gps_len+1


                    else:
                    # some other element. screw it for now, lets only find its length
                    # read the next field, it'l tell you how many key-value pairs in the segment
                        quantity = ord(data[cursor+1])

                        # not skip this element
                        cursor = cursor + quantity * 2 + 2

            for key in ['alt', 'lat', 'lon', 'ts', 'h_speed']:
                message[key] = record[key]

        response = ''.join(('0005000201'.decode('hex'),
                            avl_id,
                            chr(num_of_data)))

        return message