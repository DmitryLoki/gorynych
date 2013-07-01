__author__ = 'Boris Tsema'
import cPickle

from zope.interface import implementer
import numpy as np

from gorynych.common.infrastructure.persistence import np_as_text
from gorynych.processor.domain import track

class PickledTrackRepository(object):
    def save(self, data):
        f = open('track_repo', 'wb')
        cPickle.dump(data, f, -1)
        f.close()

NEW_TRACK = """
    INSERT INTO track (start_time, end_time, track_type, track_id)
    VALUES (%s, %s, (SELECT id FROM track_type WHERE name=%s), %s)
    RETURNING ID;
    """

INSERT_SNAPSHOT = """
    INSERT INTO track_snapshot (timestamp, id, snapshot) VALUES(%s, %s, %s)
    """

def find_snapshots(data):
    result = []
    if data._state.finish_time:
        result.append(dict(timestamp=int(data._state.finish_time),
            snapshot='finished'))
    elif data._state.end_time:
        result.append(dict(timestamp=int(data._state.end_time),
            snapshot='landed'))

    if data._state.start_time:
        result.append(dict(timestamp=int(data._state.start_time),
            snapshot='started'))
    return result


