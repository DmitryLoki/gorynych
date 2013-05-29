__author__ = 'Boris Tsema'

import math

import simplejson as json
from twisted.web.client import getPage

from gorynych import __version__

# TODO: create module with constants (like in twisted?).
EARTH_RADIUS = 6371000

class APIAccessor(object):
    '''
    Implement asynchronous methods for convinient access to JSON api.
    '''
    def __init__(self, url='api.airtribune.com', version=None):
        if not version:
            version = str(__version__)
        self.url = '/'.join((url, version))

    def get_track_archive(self, race_id):
        url = '/'.join((self.url, 'race', race_id, 'track_archive'))
        d = getPage(url)
        d.addCallback(json.loads)
        return d


def point_dist_calculator(start_lat, start_lon, end_lat, end_lon):
    """Return distance between two points in float
    TODO: analyze function and rewrite on Cython or C if needed
    """
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

