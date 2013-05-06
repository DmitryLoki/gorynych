'''
This application service return tracks data to visualisation.
'''
from twisted.internet import defer
from twisted.python import log

__author__ = 'Boris Tsema'

from collections import defaultdict

from twisted.application.service import Service


SELECT_DATA = """
    SELECT
          t.timestamp,
          string_agg(
            concat_ws(',', rt.contest_number, t.lat::text, t.lon::text, t.alt::text, t.v_speed::text, t.g_speed::text, t.distance::text),
          ';')
        FROM
          track_data t,
          race r,
          race_tracks rt,
          track tr
        WHERE
          r.race_id = %s AND
          rt.rid = r.id AND
          rt.track_id = tr.track_id AND
          t.timestamp BETWEEN %s AND %s
        GROUP BY
          t.timestamp
        ORDER BY
          t.timestamp;
    """

GET_HEADERS_DATA = """
    WITH ids AS (
        SELECT
          tr.id AS id,
          race_tracks.contest_number
        FROM
          track tr,
          race_tracks,
          race
        WHERE
          race_tracks.track_id = tr.track_id AND
          race_tracks.rid = race.id AND
          race.race_id = %s),

          tdata AS (
            SELECT
              timestamp,
              concat_ws(',', lat::text, lon::text, alt::text, v_speed::text, g_speed::text, distance::text) as data,
              trid as id,
              row_number() OVER(PARTITION BY td.trid ORDER BY td.timestamp DESC) AS rk
            FROM track_data td
            WHERE
              td.trid in (SELECT id FROM ids)
              AND td."timestamp" BETWEEN %s AND %s)

    SELECT
      i.contest_number, t.data
    FROM
      tdata t,
      ids i
    WHERE
      t.rk = 1 AND
  i.id = t.id;
  """

GET_HEADERS_SNAPSHOTS = """
    WITH ids AS (
        SELECT
          tr.id AS id,
          race_tracks.contest_number
        FROM
          track tr,
          race_tracks,
          race
        WHERE
          race_tracks.track_id = tr.track_id AND
          race_tracks.rid = race.id AND
          race.race_id = %s),
          snaps AS (
        SELECT
          snapshot,
          timestamp,
          ts.trid AS id,
          row_number() OVER(PARTITION BY ts.trid ORDER BY ts.timestamp DESC) AS rk
        FROM track_snapshot ts
        WHERE
          ts.trid in (SELECT id FROM ids)
          AND ts.timestamp <= %s)
    SELECT
      i.contest_number, s.snapshot, s.timestamp
    FROM
      snaps s,
      ids i
    WHERE
      s.rk = 1
      AND s.id = i.id;
    """

class TrackVisualizationService(Service):
    # don't show pilots earlier then time - track_gap. In seconds
    track_gap = 10800

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
        result = dict()
        race_id = params['race_id']
        from_time = int(params['from_time'])
        to_time = int(params['to_time'])
        start_positions = params.get('start_positions')
        tracks = yield self.pool.runQuery(SELECT_DATA, (race_id, from_time,
                                                  to_time))
        result['timeline'] = self.prepare_result(tracks)
        if start_positions:
            hdata = yield self.pool.runQuery(GET_HEADERS_DATA, (race_id,
                                from_time - self.track_gap, from_time))
            hsnaps = yield self.pool.runQuery(GET_HEADERS_SNAPSHOTS,
                                              (race_id, from_time))
            start_data = self.prepare_start_data(hdata, hsnaps)
            result['start'] = start_data
        defer.returnValue(result)

    def prepare_start_data(self, hdata, hsnaps):
        '''
        Prepare last state of tracks from their coordinates and snapshots.
        @param hdata: (contest_number, data)
        @type hdata: list of tuples
        @param hsnaps: (contest_number, snapshot, timestamp)
        @type hsnaps: list of tuples
        @return: {'contest_number':{'data':[alt, lon, ...],
        'state':'finished', 'statechanged_at': 2134}
        @rtype:
        '''
        result = defaultdict(dict)
        # Add last coords and speeds to result.
        for row in hdata:
            result[str(row[0])]['data'] = parse_result(row[1].split(','))

        # Add last state to result.
        for row in hsnaps:
            result[str(row[0])]['state'] = str(row[1])
            result[str(row[0])]['statechanged_at'] = int(row[2])

        for pilot in result:
            if not result[pilot].has_key('state'):
                result[pilot]['state'] = 'not started'
        return result

    def prepare_result(self, tracks):
        '''

        @param tracks: [(timestamp, contest_number,lat,lon,
        ...;contest_number,lat,lon..),...]
        @type tracks: list of tuple
        @return:{timestamp:{'contnumber':[lat,lon...], },}
        @rtype:
        '''
        result = defaultdict(dict)
        for row in tracks:
            for data in row[1].split(';'):
                result[int(row[0])][str(data.split(',')[0])
                                    ] = parse_result(data.split(',')[1:])
        return result



def parse_result(data):
    res = dict()
    res['lat'], res['lon'], res['alt'], res['vspd'], res['gspd'], \
    res['dist'] = data

    formats = dict(lat=float, lon=float, alt=int, gspd=float, vspd=float,
                   dist=int)
    for key in res:
        res[key] = formats[key](res[key])
    return res
