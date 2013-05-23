__author__ = 'Boris Tsema'

import simplejson as json
from twisted.web.client import getPage

from gorynych import __version__

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

