# coding=utf-8
from twisted.internet import defer
from twisted.python import log

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
    '''
    @param data:
    @type data: L{gorynych.processor.domain.track.Track}
    @return:
    @rtype: C{list}
    '''
    result = []
    state = data._state
    if state.started:
        result.append(dict(timestamp=state.start_time, snapshot='started'))
    if state.ended:
        result.append(dict(timestamp=state.end_time, snapshot=state.state))
    if state.finish_time:
        result.append(dict(timestamp=state.finish_time, snapshot='finished'))
    if data._state.end_time:
        result.append(dict(timestamp=int(data._state.end_time),
            snapshot='landed'))
    if state.start_time:
        result.append(dict(timestamp=state.start_time, snapshot='started'))
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

        def handle_Failure(failure):
            log.err(failure)
            return obj.reset()

        d = defer.succeed(1)
        if obj.changes:
            d.addCallback(lambda _: pe.event_store().persist(obj.changes))
        if not obj._id:
            d.addCallback(lambda _: self.pool.runInteraction(self._save_new,
                obj))
        else:
            d.addCallback(lambda _: self.pool.runInteraction(self._update,
                obj))
            d.addCallback(self._update_times)
        d.addCallback(self._save_snapshots)
        d.addCallback(lambda obj: obj.reset())
        d.addErrback(handle_Failure)
        return d

    def _save_new(self, cur, obj):
        cur.execute(NEW_TRACK, (obj._state.start_time, obj._state.end_time,
        obj.type.type, str(obj.id)))
        dbid = cur.fetchone()[0]
        log.msg("New track inserted %s and its id %s" % (obj.id, dbid))

        if len(obj.points) > 0:
            points = obj.points
            points['id'] = np.ones(len(points)) * dbid
            data = np_as_text(points)
            cur.copy_expert("COPY track_data FROM STDIN ", data)
        obj._id = dbid
        return obj

    @defer.inlineCallbacks
    def _save_snapshots(self, obj):
        snaps = find_snapshots(obj)
        for snap in snaps:
            try:
                yield self.pool.runOperation(INSERT_SNAPSHOT,
                            (snap['timestamp'], obj._id, snap['snapshot']))
            except:
                pass
        defer.returnValue(obj)

    def _update(self, cur, obj):
        if len(obj.points) == 0:
            return obj
        points = obj.points
        points['id'] = np.ones(len(points)) * obj._id
        data = np_as_text(points)
        try:
            cur.copy_expert("COPY track_data FROM STDIN ", data)
        except Exception as e:
            log.err("Error occured while COPY data on update: %r" % e)
        return obj

    def _update_times(self, obj):
        d = defer.succeed(1)
        for idx, item in enumerate(obj.changes):
            if item.name == 'TrackStarted':
                t = obj._state.start_time
                d.addCallback(lambda _:self.pool.runOperation(
                    "UPDATE track SET start_time=%s WHERE ID=%s", (t,
                        obj._id)))
            if item.name == 'TrackEnded':
                t = obj._state.end_time
                d.addCallback(lambda _:self.pool.runOperation(
                    "UPDATE track SET end_time=%s WHERE ID=%s",
                    (t, obj._id)))
        d.addCallback(lambda _:obj)
        return d
