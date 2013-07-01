from twisted.internet import defer

__author__ = 'Boris Tsema'
import cPickle

import numpy as np

from gorynych.common.infrastructure.persistence import np_as_text
from gorynych.common.infrastructure import persistence as pe
from gorynych.common.exceptions import NoAggregate
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


class TrackRepository(object):
    def __init__(self, pool):
        self.pool = pool

    @defer.inlineCallbacks
    def get_by_id(self, id):
        data = yield self.pool.runQuery(pe.select('track'), (str(id),))
        if not data:
            raise NoAggregate("%s %s" % ('Track', id))
        tid = track.TrackID.fromstring(data[0][0])
        event_list = yield pe.event_store().load_events(tid)
        result = track.Track(tid, event_list)
        result._id = data[0][1]
        defer.returnValue(result)

    def save(self, obj):
        if obj._id:
            return self.pool.runInteraction(self._save_new, obj)

    def _save_new(self, cur, obj):
        cur.execute(NEW_TRACK, (obj._state.start_time, obj._state.end_time,
                                obj.type.type, str(obj.id)))
        dbid = cur.fetchone()[0]

        points = obj.state['points']
        points['id'] = np.ones(len(points)) * dbid
        data = np_as_text(points)
        cur.copy_expert("COPY track_data FROM STDIN ", data)
        snaps = find_snapshots(obj)
        for snap in snaps:
            cur.execute(INSERT_SNAPSHOT, (snap['timestamp'], dbid,
                snap['snapshot']))
        obj._id = dbid
        return obj

