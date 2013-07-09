from operator import xor
import time

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
    pass