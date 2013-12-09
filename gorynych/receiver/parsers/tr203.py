# encoding: utf-8

import time
from operator import xor

from gorynych.receiver.parsers import IParseMessage
from zope.interface import implementer

MIN_SATTELITE_NUMBER = 2
MAXIMUM_HDOP = 10


@implementer(IParseMessage)
class GlobalSatTR203(object):

    def __init__(self):
        self.format = dict(type=0, imei=1, lon=5, lat=6, alt=7,
                           h_speed=8, battery=10)
        self.convert = dict(type=str, imei=str, lat=self.latitude,
                            lon=self.longitude, alt=int, h_speed=self.speed,
                            battery=str)

    def speed(self, speed):
        return float(speed)

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
                raise ValueError("Bad GPS or message type.")
        except Exception as e:
            raise ValueError(str(e))
        return msg

    def parse(self, msg):
        arr = msg.split('*')[0].split(',')
        result = dict()
        for key in self.format.keys():
            result[key] = self.convert[key](arr[self.format[key]])
        result['ts'] = int(time.mktime(
            time.strptime(''.join((arr[3], arr[4])), '%d%m%y%H%M%S')))
        return result

    def _message_is_good(self, msg):
        arr = msg.split('*')[0].split(',')
        gsr = arr[0]
        hdop = float(arr[9])
        fix = int(arr[2])
        return gsr == 'GSr' and hdop <= MAXIMUM_HDOP and fix == 3
