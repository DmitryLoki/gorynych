import time

from twisted.internet import defer
from twisted.trial import unittest
import numpy as np

from gorynych.info.infrastructure.test.test_psql_repository import MockeryTestCase
from gorynych.processor.infrastructure import persistence
from gorynych.processor.domain import track
from gorynych.info.infrastructure.test import db_helpers
from gorynych.common.domain import events


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
    repo_type = persistence.TrackRepository
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
        t = track.Track(track.TrackID(), [])
        t._type = track.track_types('online')
        t.processed = np.array([], dtype=track.DTYPE)
        return t

    def _get_points(self, data):
        points = np.empty(len(data), dtype=track.DTYPE)
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
        track.points = np.array([], dtype=track.DTYPE)
        yield self.repo.save(track)
        retrieved_data = yield POOL.runQuery(DATA_QUERY, (str(track.id),))
        self.assertEquals(len(retrieved_data), 2)
        self._compare_points(retrieved_data, self.data)


class TestGetStatesFromEvents(unittest.TestCase):
    def setUp(self):
        self.track = track.Track(track.TrackID(), [])

    def tearDown(self):
        del self.track

    def test_empty_events(self):
        res = persistence.get_states_from_events(self.track)
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res), 0)

    def test_some_events(self):
        t = int(time.time())
        ev1 = events.TrackStarted(track.TrackID(), None, 'track', t)
        ev2 = events.TrackFinished(track.TrackID(), None, 'track', t + 1)
        self.track.apply(ev1)
        self.track.apply(ev2)
        res = persistence.get_states_from_events(self.track)
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res), 2)
        for key, val in res.iteritems():
            if 'started' in val:
                self.assertEqual(key, t)
            elif 'finished' in val:
                self.assertEqual(key, t + 1)
            else:
                self.fail("Only started or finished state expected.")

    def test_duplicated_events(self):
        t = int(time.time())
        ev1 = events.TrackStarted(track.TrackID(), None, 'track', t)
        ev2 = events.TrackStarted(track.TrackID(), None, 'track', t + 1)
        ev3 = events.TrackStarted(track.TrackID(), None, 'track', t + 1)
        self.track.apply(ev1)
        self.track.apply(ev2)
        self.track.apply(ev3)
        res = persistence.get_states_from_events(self.track)
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res), 2)
        self.assertEqual(len(res[t+1]), 1)

    def test_two_events_in_one_time(self):
        t = int(time.time())
        ev1 = events.TrackFinishTimeReceived(track.TrackID(), t, 'track', t)
        ev2 = events.TrackLanded(track.TrackID(), t, 'track', t)
        self.track.apply(ev1)
        self.track.apply(ev2)
        res = persistence.get_states_from_events(self.track)
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[t]), 2)
        self.assertSetEqual(res[t], set(['in_air_false', 'es_taken']))

    def test_unwanted_event(self):
        t = int(time.time())
        ev1 = events.TrackSlowedDown(track.TrackID())
        self.track.apply(ev1)
        res = persistence.get_states_from_events(self.track)
        self.assertIsInstance(res, dict)
        self.assertEqual(len(res), 0)

