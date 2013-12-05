__author__ = 'Boris Tsema'

import math
import decimal

import requests
import simplejson as json
from twisted.python import log
from twisted.web.client import getPage
from twisted.internet import defer, task
from twisted.application.service import Service

from gorynych import __version__, OPTS
from gorynych.common.exceptions import BadCheckpoint

# TODO: create module with constants (like in twisted?).
EARTH_RADIUS = 6371000

from twisted.web.client import HTTPClientFactory
HTTPClientFactory.noisy = False


class AsynchronousAPIAccessor(object):
    def __init__(self, url=None, version=None):
        if not version:
            version = str(__version__)
        if not version.startswith('v'):
            version = 'v' + version
        if not url:
            url = OPTS['apiurl']
            if url.endswith('/'):
                url = url[:-1]
        self.url = '/'.join((url, version))

    def _return_page(self, url):
        d = getPage(url)
        d.addCallback(json.loads)
        d.addErrback(lambda _: None)
        return d

    def get_contest_races(self, contest_id):
        url = '/'.join((self.url, 'contest', contest_id, 'race'))
        return self._return_page(url)


# TODO: do all of this in async way.
class APIAccessor(object):
    '''
    Implement asynchronous methods for convinient access to JSON api.
    '''
    def __init__(self, url=None, version=None):
        if not version:
            version = str(__version__)
        if not version.startswith('v'):
            version = 'v' + version
        if not url:
            url = OPTS['apiurl']
            if url.endswith('/'):
                url = url[:-1]
        self.url = '/'.join((url, version))

    def get_track_archive(self, race_id):
        url = '/'.join((self.url, 'race', race_id, 'track_archive'))
        return self._return_page(url)

    def get_race_task(self, race_id):
        url = '/'.join((self.url, 'race', race_id))
        return self._return_page(url)

    def _return_page(self, url):
        r = requests.get(url)
        if not r.status_code == 200:
            return None
        try:
            result = r.json()
        except Exception as e:
            log.err("Error while doing json in APIAccessor for %s: %r" %
                    (r.text, e))
            raise e
        return result


class SinglePollerService(Service):
    """
    This is a service which gets a pollable object and asks its method read()
    every time specified. Results are handled in handle_payload method.
    """
    def __init__(self, connection, polling_interval, **read_args):
        self.connection = connection
        self.polling_interval = polling_interval
        self.read_args = read_args

    def _start_polling(self):
        self.poller = task.LoopingCall(self.poll, **self.read_args)
        return self.poller

    def poll(self, **kwargs):
        d = self.connection.read(**kwargs)
        return d.addCallback(lambda data: self.handle_payload(kwargs.values(), *data))

    def handle_payload(self, data):
        """
        Override this method
        """
        pass

    def startService(self):
        d = defer.Deferred()
        d.addCallback(lambda _: Service.startService(self))
        d.addCallback(lambda _: log.msg("Poller is started"))
        d.addCallback(lambda _: self.connection.connect())
        d.addCallback(lambda ready_connection: ready_connection.open(**self.read_args))
        d.addCallback(lambda _: self._start_polling())
        d.addCallback(lambda lc: lc.start(self.polling_interval))
        d.callback('run!')
        return d

    def stopService(self):
        self.poller.stop()
        Service.stopService(self)


def point_dist_calculator(start_lat, start_lon, end_lat, end_lon):
    """Return distance between two points in float
    TODO: analyze function and rewrite on Cython or C if needed
    """
    # raise ValueError(repr(start_lat), repr(start_lon), repr(end_lat),
    #     type(end_lon))
    # raise ValueError(start_lat, start_lon, end_lat, end_lon)
    start_lat = float(math.radians(float(start_lat)))
    start_lon = float(math.radians(float(start_lon)))
    end_lat = float(math.radians(float(end_lat)))
    end_lon = float(math.radians(float(end_lon)))
    d_lat = end_lat - start_lat
    d_lon = end_lon - start_lon
    df = 2 * math.asin(
        math.sqrt(
            math.sin(d_lat/2)**2 + math.cos(start_lat) * math.cos(end_lat) * math.sin(d_lon/2)**2))
    c = df * EARTH_RADIUS
    return c


def bearing(start_lat, start_lon, end_lat, end_lon):
    '''
    Calculate bearing between points.
    @param start_lat:
    @type start_lat:
    @param start_lon:
    @type start_lon:
    @param end_lat:
    @type end_lat:
    @param end_lon:
    @type end_lon:
    @return:
    @rtype:
    '''
    point1 = (float(start_lat), float(start_lon))
    point2 = (float(end_lat), float(end_lon))
    if point1 == point2:
        return 0
    lat1 = point1[0] * math.pi / 180
    lat2 = point2[0] * math.pi / 180
    lon1 = point1[1] * math.pi / 180
    lon2 = point2[1] * math.pi / 180

    cl1, cl2 = math.cos(lat1), math.cos(lat2)
    sl1, sl2 = math.sin(lat1), math.sin(lat2)
    cdelta = math.cos(lon2 - lon1)
    sdelta = math.sin(lon2 - lon1)

    # bearing calculation
    x = (cl1 * sl2) - (sl1 * cl2 * cdelta)
    y = sdelta * cl2
    try:
        z = math.degrees(math.atan(y / x))
    except ZeroDivisionError:
        return 0
    if x < 0:
        z = z + 180
    return (z + 360.) % 360.


def times_from_checkpoints(checkpoints):
    '''
    Look for checkpoints and get race times from them.
    @param checkpoints:
    @type checkpoints:
    @return: tuple of ints
    @rtype: C{tuple}
    '''
    assert isinstance(checkpoints, list), "I'm waiting for a list."
    start_time = decimal.Decimal('infinity')
    end_time = None
    for point in checkpoints:
        if point.open_time:
            if int(point.open_time) < start_time:
                start_time = point.open_time
        if point.close_time:
            if int(point.close_time) > end_time:
                end_time = int(point.close_time)
    if start_time < end_time:
        return int(start_time), int(end_time)
    else:
        raise BadCheckpoint("Wrong or absent times in checkpoints.")

