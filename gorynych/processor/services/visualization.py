'''
This application service return tracks data to visualisation.
'''
import time
import math
from collections import defaultdict

from twisted.application.service import Service
from twisted.internet import defer
from twisted.python import log
import simplejson as json

__author__ = 'Boris Tsema'


# Select track data.
SELECT_DATA = """
    SELECT
      t.timestamp,
      string_agg(
        concat_ws(',', tg.track_label, t.lat::text, t.lon::text, t.alt::text, t.v_speed::text, t.g_speed::text, t.distance::text),
      ';')
    FROM
      track_data t,
      tracks_group tg
    WHERE
      t.id = tg.track_id AND
      tg.group_id = %s AND
      t.timestamp BETWEEN %s AND %s
    GROUP BY
      t.timestamp
    ORDER BY
      t.timestamp;
    """

# Select track state.
SELECT_DATA_SNAPSHOTS = """
    SELECT
      s.timestamp,
      s.snapshot,
      tg.track_label
    FROM
      track_snapshot s,
      tracks_group tg
    WHERE
      s.id = tg.track_id AND
      tg.group_id = %s AND
      s.timestamp BETWEEN %s AND %s;
    """

# Select track data just for some tracks.
SELECT_DATA_BY_LABEL = """
    SELECT
      t.timestamp,
      string_agg(
        concat_ws(',', tg.track_label, t.lat::text, t.lon::text, t.alt::text, t.v_speed::text, t.g_speed::text, t.distance::text),
      ';')
    FROM
      track_data t,
      tracks_group tg
    WHERE
      t.id = tg.track_id AND
      tg.group_id = %s AND
      t.timestamp BETWEEN %s AND %s AND
      tg.track_label in %s
    GROUP BY
      t.timestamp
    ORDER BY
      t.timestamp;
    """

# Select track state changes for some tracks.
SELECT_DATA_SNAPSHOTS_BY_LABEL = """
    SELECT
      s.timestamp,
      s.snapshot,
      tg.track_label
    FROM
      track_snapshot s,
      tracks_group tg
    WHERE
      s.id = tg.track_id AND
      tg.group_id = %s AND
      s.timestamp BETWEEN %s AND %s AND
      tg.track_label in %s;
    """

# Select last track point in the past for every track.
GET_HEADERS_DATA = """
    WITH tdata AS (
            SELECT
              timestamp,
              concat_ws(',', lat::text, lon::text, alt::text, v_speed::text, g_speed::text, distance::text) as data,
              td.id,
              row_number() OVER(PARTITION BY td.id ORDER BY td.timestamp DESC) AS rk
            FROM track_data td,
                tracks_group tg
            WHERE
              td.id = tg.track_id
              AND tg.group_id = %s
              AND td."timestamp" BETWEEN %s AND %s)

    SELECT
      tg.track_label, t.data, t.timestamp
    FROM
      tdata t,
      tracks_group tg
    WHERE
      t.rk = 1 AND
      tg.track_id = t.id;
  """

# Select last state in the past for every track.
GET_HEADERS_SNAPSHOTS = """
    WITH
      snaps AS (
        SELECT
          snapshot,
          timestamp,
          ts.id AS id,
          tg.track_label as track_label,
          row_number() OVER(PARTITION BY ts.id ORDER BY ts.timestamp DESC) AS rk
        FROM
            track_snapshot ts,
            tracks_group tg
        WHERE
          ts.id = tg.track_id AND
          tg.group_id = %s
          AND ts.timestamp <= %s)
    SELECT
      s.track_label, s.snapshot, s.timestamp
    FROM
      snaps s,
      tracks_group tg
    WHERE
      s.rk < 3
      AND s.id = tg.track_id;
    """


class TrackVisualizationService(Service):
    # Don't show pilots earlier then time - track_gap. In seconds
    track_gap = 15000

    def __init__(self, pool):
        self.pool = pool

    def startService(self):
        Service.startService(self)
        log.msg("Starting DB pool")
        return self.pool.start()

    def stopService(self):
        Service.stopService(self)
        return self.pool.close()

    @defer.inlineCallbacks
    def get_track_data(self, params):
        '''
        Return dict with track data according to specified protocol.
        @param params: request parameters, consist of group_id (domain id of
         tracks group), from_time (unixtime) to_time (unixtime),
         start_positions (show of not last track's position in the past),
         track_labels (return result only for tracks with specified labels).
        @type params: dict
        @return:
        @rtype: dict
        '''
        # TODO: pass keyword arguments into function instead of dictionary.
        result = dict()
        group_id = params['group_id']
        from_time = int(params['from_time'])
        to_time = int(params['to_time'])
        start_positions = params.get('start_positions')
        track_labels = params.get('track_labels', '')
        t1 = time.time()

        if track_labels:
            track_labels = track_labels.split(',')
            tracks = yield self.pool.runQuery(SELECT_DATA_BY_LABEL,
                (group_id, from_time,
                to_time, tuple(track_labels)))
            snaps = yield self.pool.runQuery(SELECT_DATA_SNAPSHOTS_BY_LABEL,
                (group_id, from_time, to_time, tuple(track_labels)))

        else:
            tracks = yield self.pool.runQuery(SELECT_DATA,
                (group_id, from_time,
                to_time))
            snaps = yield self.pool.runQuery(SELECT_DATA_SNAPSHOTS,
                (group_id, from_time, to_time))

        t2 = time.time()
        result['timeline'] = self.prepare_result(tracks, snaps)
        log.msg("data requested in %0.3f" % (t2 - t1))
        if start_positions:
            ts1 = time.time()
            hdata = yield self.pool.runQuery(GET_HEADERS_DATA, (group_id,
            from_time - self.track_gap, from_time))
            hsnaps = yield self.pool.runQuery(GET_HEADERS_SNAPSHOTS,
                (group_id, from_time))
            ts2 = time.time()
            start_data = self.prepare_start_data(hdata, hsnaps)
            result['start'] = start_data
            log.msg("start positions requested in %0.3f" % (ts2 - ts1))
        defer.returnValue(result)

    def prepare_start_data(self, hdata, hsnaps):
        '''
        Prepare last state of tracks from their coordinates and snapshots.
        @param hdata: (contest_number, data, timestamp)
        @type hdata: list of tuples
        @param hsnaps: (contest_number, snapshot, timestamp)
        @type hsnaps: list of tuples
        @return: {'contest_number':{'data':[alt, lon, ...],
        'state':'finished', 'statechanged_at': 2134} - that's not true
        @rtype:
        '''
        # TODO: make this method static.
        result = defaultdict(dict)
        # Add last coords and speeds to result.
        for row in hdata:
            cont_number, data, timestamp = row
            result[cont_number] = parse_result(data.split(','))

        # Add last state to result.
        for row in hsnaps:
            cont_number, state, state_ts = row
            try:
                state = json.loads(state)
                if 'in_air_true' in state:
                    result[cont_number]['in_air'] = True
                    del state[state.index('in_air_true')]
                if 'in_air_false' in state:
                    result[cont_number]['in_air'] = False
                    del state[state.index('in_air_false')]
                if 'es_taken' in state:
                    result[cont_number]['finish_time'] = int(state_ts)

                if len(state) > 0:
                    result[cont_number]['state'] = state[0]
            except:
                continue

        for contest_number in result:
            if not result[contest_number].has_key('state'):
                result[contest_number]['state'] = 'not started'
            if not result[contest_number].has_key('in_air'):
                # TODO: everybody in air by default, is it ok?
                result[contest_number]['in_air'] = True
        return result

    def prepare_result(self, tracks, snaps):
        '''

        @param tracks: [(timestamp, contest_number,lat,lon,
        ...;contest_number,lat,lon..),...]
        @param snaps: [(timestamp, snapshot, contest_number), ...]
        @type tracks: list of tuple
        @return:{timestamp:{'contnumber':[lat,lon...], },}
        @rtype:
        '''
        # TODO: does this method need to be part of interface or it can be
        # static ?
        result = defaultdict(dict)
        for row in tracks:
            for data in row[1].split(';'):
                result[int(row[0])][str(data.split(',')[0])
                ] = parse_result(data.split(',')[1:])

        for row in snaps:
            timestamp, snapshot, contest_number = row
            if result[timestamp].has_key(contest_number):
                concrete_pilot = result[timestamp][contest_number]
                try:
                    snapshot = json.loads(snapshot)
                    if 'in_air_true' in snapshot:
                        concrete_pilot['in_air'] = True
                        del snapshot[snapshot.index('in_air_true')]
                    elif 'in_air_false' in snapshot:
                        concrete_pilot['in_air'] = False
                        del snapshot[snapshot.index('in_air_false')]
                except:
                    continue
                if len(snapshot) > 0:
                    concrete_pilot['state'] = snapshot[0]

        return result


def parse_result(data):
    res = dict()
    res['lat'], res['lon'], res['alt'], res['vspd'], res['gspd'], \
        res['dist'] = data

    def _float(num):
        result = round(float(num), 6)
        if math.isnan(result):
            log.msg("Nan found in float.")
            result = 0
        if math.isinf(result):
            log.msg("Infinity found in float.")
            result = 1
        return result

    formats = dict(lat=_float, lon=_float, alt=int, gspd=_float, vspd=_float,
        dist=int)
    for key in res:
        res[key] = formats[key](res[key])
    return dict(dist=res['dist'],
        spds=[res['gspd'], res['vspd']],
        crds=[res['lat'], res['lon'], res['alt']])
