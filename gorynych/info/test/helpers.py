__author__ = 'Boris Tsema'

import os
import cPickle

from zope.interface import implements

from gorynych.info.domain.contest import IContestRepository
from gorynych.info.domain.race import IRaceRepository
from gorynych.info.domain.person import IPersonRepository
from gorynych.common.exceptions import NoAggregate

class BaseRepository(object):

    def __init__(self, filename):
        self.filename = filename
        if not os.path.isfile(filename):
            with open(filename, 'wb') as f:
                cPickle.dump({}, f, -1)

    def save(self, obj):
        if not obj:
            return None
        with open(self.filename, 'rb') as f:
            data = cPickle.load(f)
        with open(self.filename, 'wb') as f:
            data[obj.id] = obj
            cPickle.dump(data, f, -1)
            return obj

    def get_by_id(self, id):
        with open(self.filename, 'rb') as f:
            data = cPickle.load(f)
            try:
                return data[id]
            except KeyError:
                raise NoAggregate

    def get_list(self, limit=None, offset=None):
        with open(self.filename, 'rb') as f:
            data = cPickle.load(f)
            if not data:
                return None
            return data.values()


class PickleContestRepository(BaseRepository):
    implements(IContestRepository)


class PickleRaceRepository(BaseRepository):
    implements(IRaceRepository)


class PicklePersonRepository(BaseRepository):
    implements(IPersonRepository)

