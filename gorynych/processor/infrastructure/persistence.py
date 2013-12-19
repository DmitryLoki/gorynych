# coding=utf-8
__author__ = 'Boris Tsema'
import time
import cPickle
from collections import defaultdict
import json
import re

import numpy as np
from twisted.internet import defer
from twisted.python import log

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
    @return: dict with timestamp as a key and state set as a value.
    @rtype: C{dict}
    '''
    result = defaultdict(set)
    state = data._state
    # Every track is in air from it's first point by default.
    # TODO: change it someday.
    if len(data.points) == 0:
        return result
    result[int(data.points['timestamp'][0])].add('in_air_true')
    if not state.in_air and state.in_air_changed:
        result[int(state.in_air_changed)].add('in_air_false')
    if state.state == 'finished':
        result[int(state.statechanged_at)].add('finished')
    if state.finish_time:
        result[int(state.finish_time)].add('es_taken')
    if state.start_time:
        result[int(state.start_time)].add('started')
    return result


class TrackRepository(object):

    duplicate_key_ts = r'Key.*\((\d*)\,.*already exists'

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
            d.addCallback(lambda _: self.pool.runWithConnection(self._update,
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
            try:
                cur.copy_expert("COPY track_data FROM STDIN ", data)
            except Exception as e:
                log.err("Exception occured on inserting points: %r" % e)
                obj.buffer = np.empty(0, dtype=track.DTYPE)
        obj._id = dbid
        return obj

    @defer.inlineCallbacks
    def _save_snapshots(self, obj):
        snaps = find_snapshots(obj)
        for snap in snaps:
            try:
                yield self.pool.runOperation(INSERT_SNAPSHOT,
                            (snap, obj._id, json.dumps(list(snaps[snap]))))
            except Exception as e:
                log.err("Error while inserting snapshot %s:%s for track %s: "
                        "%r" %
                        (snap, snaps[snap], obj._id, e))
        defer.returnValue(obj)

    def _update(self, con, obj):
        if len(obj.points) == 0:
            return obj
        tdiff = int(time.time()) - obj.points[0]['timestamp']
        log.msg("Save %s points for track %s" % (len(obj.points), obj._id))
        log.msg("First points for track %s was %s second ago." % (obj._id,
            tdiff))

        def try_insert_points(points):
            data = np_as_text(points)
            cur = con._connection.cursor()
            cur.copy_expert("COPY track_data FROM STDIN ", data)

        points = obj.points
        points['id'] = np.ones(len(points)) * obj._id

        while True:
            try:
                try_insert_points(points)
                break
            except Exception as e:
                if e.pgcode == '23505':
                    dup_tc = re.findall(self.duplicate_key_ts, e.message)
                    if not dup_tc:
                        break
                    dup_tc = int(dup_tc[0])
                    idx = np.where(points['timestamp'] != dup_tc)
                    points = points[idx]
                    if len(points) == 0:
                        break
                    con._connection.rollback()
                else:
                    log.err("Error occured while COPY data on update for track %s: "
                            "%r" % (obj._id, e))
                    obj.buffer = np.empty(0, dtype=track.DTYPE)
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
