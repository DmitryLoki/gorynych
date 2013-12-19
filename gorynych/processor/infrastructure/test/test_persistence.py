from gorynych.info.infrastructure.test.test_psql_repository import MockeryTestCase
from gorynych.processor.infrastructure.persistence import TrackRepository
from gorynych.processor.domain.track import Track, TrackID, DTYPE, track_types
from gorynych.info.infrastructure.test import db_helpers

from twisted.internet import defer
import numpy as np
import time

POOL = db_helpers.POOL

DATA_QUERY = """
    SELECT
        td.*
    FROM
        track_data td,
        track t
    WHERE
        t.id = td.id and
        t.track_id=%s;
    """


class TrackRepositoryTestCase(MockeryTestCase):
    repo_type = TrackRepository
    sql_file = 'track'
    data = [{
            'timestamp': int(time.time()),
            'lat': 21.21233,
            'lon': 22.34343,
            'alt': 121,
            'g_speed': 23.0,
            'v_speed': 4.33,
            'distance': 1,
        },
            {
                'timestamp': int(time.time()) + 50,
                'lat': 21.51233,
                'lon': 22.24343,
                'alt': 120,
                'g_speed': 20.0,
                'v_speed': 3.44,
                'distance': 1,
            }]

    def _sample(self):
        t = Track(TrackID(), [])
        t._type = track_types('online')
        t.processed = np.array([], dtype=DTYPE)
        return t

    def _get_points(self, data):
        points = np.empty(len(data), dtype=DTYPE)
        for i, item in enumerate(data):
            for key in item.keys():
                points[i][key] = item[key]
        return points

    def _compare_points(self, fromdb, expected):
        cleaned_data = []
        for row in fromdb:
            lrow = list(row)[1:]
            p = {}
            p['timestamp'], p['lat'], p['lon'], p['alt'], p['g_speed'], \
                p['v_speed'], p['distance'] = lrow
            cleaned_data.append(p)
        self.assertEquals(cleaned_data, expected)

    @defer.inlineCallbacks
    def test_add_normal_points(self):
        track = self._sample()
        track.points = self._get_points(self.data)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        self._compare_points(retrieved_data, self.data)

    @defer.inlineCallbacks
    def test_add_duplicate_points(self):
        track = self._sample()
        track.points = self._get_points(self.data)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        # same points again plus one unique
        newdata = self.data + [{
            'timestamp': int(time.time()) + 150,
            'lat': 51.51233,
            'lon': 25.24343,
            'alt': 110,
            'g_speed': 23.0,
            'v_speed': 2.34,
            'distance': 4,
        }]
        track.points = self._get_points(newdata)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 3)  # should be 3 points, new unique must survive
        self._compare_points(retrieved_data, newdata)

    @defer.inlineCallbacks
    def test_add_completely_duplicate_points(self):
        track = self._sample()
        track.points = self._get_points(self.data)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        # now insert some duplicate points
        track.points = self._get_points(self.data)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        self._compare_points(retrieved_data, self.data)

    @defer.inlineCallbacks
    def test_save_track_with_points_then_without_points(self):
        track = self._sample()
        track.points = self._get_points(self.data)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        # now insert some duplicate points
        track.points = np.array([], dtype=DTYPE)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        self._compare_points(retrieved_data, self.data)
