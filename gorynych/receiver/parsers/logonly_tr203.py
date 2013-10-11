# encoding: utf-8

import time
from operator import xor

from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

MIN_SATTELITE_NUMBER = 2
MAXIMUM_HDOP = 10


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
