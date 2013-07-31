# encoding: utf-8

from operator import xor

from zope.interface import implementer
from gorynych.receiver.parsers import IParseMessage


@implementer(IParseMessage)
class MobileTracker(object):
    def __init__(self):
        self.format = dict(imei=0, lat=1, lon=2, alt=3,
                           h_speed=4, ts=5)
        self.convert = dict(imei=str, lat=float,
                            lon=float, alt=int, h_speed=float,
                            ts=int)

    def _separate_checksum(self, msg):
        delimeter = msg.index('*')
        data = msg[:delimeter]
        checksum = msg[delimeter + 1:]
        return data, checksum

    def check_message_correctness(self, msg):
        try:
            data, checksum = self._separate_checksum(msg)
            calculated_checksum = reduce(xor, map(ord, data))
            if calculated_checksum != int(checksum):
                raise ValueError("Incorrect checksum")
        except Exception as e:
            raise ValueError(str(e))
        return msg

    def parse(self, msg):
        data, checksum = self._separate_checksum(msg)
        data = data.split(',')
        result = dict()
        for key in self.format.keys():
            result[key] = self.convert[key](data[self.format[key]])
        return result
