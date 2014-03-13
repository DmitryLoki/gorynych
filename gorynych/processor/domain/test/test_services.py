import unittest
import time

import numpy as np
from shapely.geometry import Point
from zope.interface.verify import verifyObject

from gorynych.processor.domain import services, track
from gorynych.common.domain.types import Checkpoint
from gorynych.common.domain import events
from gorynych.processor.interfaces import ITrackType


class TestOfflineCorrectorService(unittest.TestCase):
    def setUp(self):
        self.dtype = [('id', 'i4'), ('timestamp', 'i4'), ('lon', 'f4')]
        self.oc = services.OfflineCorrectorService()
        shape = 15
        ar = np.empty(shape, dtype=self.dtype)
        ar['id'] = np.ones(shape)
        ar['timestamp'] = np.arange(10, shape+10)
        ar['lon'] = np.ones(shape)
        self.ar = ar

    def tearDown(self):
        del self.ar

    def test_clean_timestamp_cut_track(self):
        result = self.oc._clean_timestamps(self.ar, 11, 20)
        self.assertIsInstance(result, np.ndarray)
        self.assertTupleEqual((result.ndim, result.shape), (1, (10,)))

    def test_clean_timestamp_remove_duplicates(self):
        self.ar['timestamp'][4] = self.ar['timestamp'][3]
        result = self.oc._clean_timestamps(self.ar, 11, 20)
        self.assertIsInstance(result, np.ndarray)
        self.assertTupleEqual((result.ndim, result.shape), (1, (9,)))
        expected = range(11, 21)
        del expected[3]
        self.assertListEqual(list(result['timestamp']), expected)

    def test_clean_timestamp_remove_reverse_points(self):
        self.ar['timestamp'][6] = self.ar['timestamp'][5] - 1
        result = self.oc._clean_timestamps(self.ar, 11, 20)
        self.assertIsInstance(result, np.ndarray)
        self.assertTupleEqual((result.ndim, result.shape), (1, (9,)))
        expected = range(11, 21)
        del expected[5]
        self.assertListEqual(list(result['timestamp']), expected)


class TestParaglidingTrackCorrector(unittest.TestCase):
    def setUp(self):
        self.dtype =[('id', 'i4'), ('timestamp', 'i4'), ('lat', 'f4'),
            ('lon', 'f4'), ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
            ('distance', 'i4')]
        self.shape = 15
        self.ar = np.empty(self.shape, dtype=self.dtype)

    def test_correct_data_ideal(self):
        self.ar['id'] = np.arange(10, self.shape +10)
        self.ar['timestamp'] = np.arange(10, self.shape +10)
        self.ar['lon'] = np.arange(self.shape)
        self.ar['alt'] = np.ones(self.shape)*60
        self.ar['lat'] = np.arange(self.shape)
        co = services.ParaglidingTrackCorrector()
        result = co.correct_data(self.ar)
        self.assertEqual(result.dtype, self.dtype)

    def test_mark_outside_altitudes(self):
        co = services.ParaglidingTrackCorrector()
        self.ar['alt'] = np.ones(self.shape)*60
        self.ar['lat'] = np.arange(self.shape)
        res = co._mark_outside_altitudes(self.ar)
        self.assertEqual(res[0].ndim, 1)
        self.assertEqual(len(res[0]), 0)
        self.assertListEqual(list(res[1]['alt']),
            list(np.ones(self.shape)*60))

    def test_correct_data_bad_alts(self):
        ar = self.ar
        ar['id'] = np.arange(10, self.shape +10)
        ar['timestamp'] = np.arange(10, self.shape +10)
        ar['lon'] = np.arange(self.shape)
        ar['alt'] = np.ones(self.shape)*60
        ar['lat'] = np.arange(self.shape)
        ar['alt'][5] = 0
        ar['alt'][10] = 100000
        co = services.ParaglidingTrackCorrector()
        res = co.correct_data(ar)
        self.assertEqual(res.shape[0], self.shape)


class TestOptDistCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = services.JavaScriptShortWay()

    def test_test(self):
        ch1 = Checkpoint('D01', Point(43.9785, 6.48), 'TO',
            (1347711300, 1347716700), 1)
        ch2 = Checkpoint('D01', Point(43.9785, 6.48), 'ss',
            (1347711300, 1347716700), 3000)
        ch3 = Checkpoint('B46', Point(44.371167, 6.309833), 'ss',
            (1347711300, 1347716700), 21000)
        ch4 = Checkpoint('B20', Point(43.951167, 6.370833), 'ss',
            (1347711300, 1347716700), 2000)
        ch5 = Checkpoint('B43', Point(44.045500, 6.360167), 'ss',
            (1347714900, 1347732000), 400)
        ch6 = Checkpoint('B37', Point(43.965833, 6.557833), 'es',
            (1347714900, 1347732000), radius=1500)
        ch7 = Checkpoint('b37', Point(43.965833, 6.557833), 'goal',
            (1347714900, 1347732000), 1000)

        chlist = [ch1, ch2, ch3, ch4, ch5, ch6, ch7]
        # for ch in chlist:
        #     print json.dumps(ch.__geo_interface__)
        res = self.calculator.calculate(chlist)
        self.assertAlmostEqual(res[1]/1000, 74.0, 0)

    def test_zero_divizion_error(self):
        # 2013 Vrsac Open Task 3
        ch1 = Checkpoint('SV01', Point(45.12298, 21.32548), 'TO', (1,2), 400)
        ch2 = Checkpoint('V021', Point(45.1525, 21.36667), 'SS', (1, 2), 1000)
        ch3 = Checkpoint('SV01', Point(45.12298, 21.32548), 'TO', (1,2), 400)
        ch4 = Checkpoint('V005', Point(45.16022, 21.37648), radius=1000)
        ch5 = Checkpoint('V027', Point(45.01683, 21.27728), radius=400)
        ch6 = Checkpoint('V060', Point(44.8502, 21.33993), radius=400)
        ch7 = Checkpoint('V045', Point(44.87575, 21.35838), radius=400)
        chlist = [ch1, ch2, ch3, ch4, ch5, ch6, ch7]
        res = self.calculator.calculate(chlist)[1]
        self.assertAlmostEqual(res/1000, 48.5, 0)


class TestParagliderSkyEarth(unittest.TestCase):
    def setUp(self):
        tid = track.TrackID()
        tc = events.TrackCreated(tid, {'race_task': 1, 'track_type': 2},
            'track')
        trackstate = track.TrackState(tid, [tc])
        self.pse = services.ParagliderSkyEarth(trackstate)
        self.d = np.zeros(5, dtype=track.DTYPE)

    def tearDown(self):
        del self.pse
        del self.d

    def test_init(self):
        self.assertIsNone(self.pse._bs)
        self.assertIsNone(self.pse._bf)
        self.assertFalse(self.pse._in_air)
        self.assertEqual(self.pse._state, 'not started')

    def test_speed_exceeded(self):
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['g_speed'] = [10, 15, 10, 15, 20]
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertTrue(len(res) > 0)
        self.assertTrue(self.pse._in_air)
        self.assertEqual(self.pse._bf, t1 + 6)
        self.assertEqual(res[0].occured_on, t1 + 6)

    def test_slowed_down(self):
        self.pse._in_air = True
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['g_speed'] = [20, 20, 15, 10, 9]
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertTrue(len(res) == 2)
        self.assertTrue(self.pse._in_air)
        self.assertIsNone(self.pse._bf)
        self.assertEqual(self.pse._bs, t1 + 67)
        self.assertEqual((res[0].occured_on, res[1].occured_on),
            (t1, t1 + 67))

    def test_landed(self):
        t1 = int(time.time())
        self.pse._in_air = True
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['alt'] = [100, 101, 103, 99, 100]
        self.d['g_speed'] = [19, 9, 9, 5, 3]
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertEqual(self.pse._bs, t1 + 6)
        self.assertIsNone(self.pse._bf)
        self.assertFalse(self.pse._in_air)

    def test_sloweddown_when_accelerated(self):
        self.pse._in_air = True
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['alt'] = [100, 101, 103, 99, 100]
        self.d['g_speed'] = [9, 11, 9, 5, 15]
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertTrue(self.pse._in_air)
        self.assertIsNone(self.pse._bs)
        self.assertEqual(self.pse._bf, t1 + 67)

    def test_landed_when_accelerated(self):
        self.pse._in_air = True
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 61, t1 + 67]
        self.d['alt'] = [100, 101, 103, 99, 150]
        self.d['g_speed'] = [9, 1, 9, 5, 15]
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertFalse(self.pse._in_air)
        self.assertEqual(self.pse._bs, t1)
        self.assertIsNone(self.pse._bf)

    def test_flyed_lagged_sloweddown(self):
        self.d['timestamp'] = [1, 72, 132, 142, 190]
        self.d['alt'] = [1935, 1829, 1775, 1775, 1773]
        self.d['g_speed'] = [8.6111, 9.7222, 9.4444, 7.77778, 9.7222]
        self.pse._in_air = True
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertFalse(self.pse._in_air) # In livetracking it should be
        # true for bad trackers.

    def test_become_in_air(self):
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['alt'] = [100, 101, 103, 99, 100]
        self.d['g_speed'] = [9, 11, 19, 15, 15]
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertIsNone(self.pse._bs)
        self.assertEqual(self.pse._bf, t1 + 6)
        self.assertTrue(self.pse._in_air)
        self.assertEqual(len(res), 2)

    def test_track_still_not_in_air(self):
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['alt'] = [100, 101, 103, 99, 100]
        self.d['g_speed'] = [9, 11, 19, 5, 15]
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertFalse(self.pse._in_air)

    def test_sloweddown_but_still_in_air(self):
        self.pse._in_air = True
        t1 = int(time.time())
        self.d['timestamp'] = [t1, t1 + 6, t1 + 20, t1 + 40, t1 + 67]
        self.d['alt'] = [100, 101, 123, 99, 100]
        self.d['g_speed'] = [9, 1, 9, 5, 5]
        self.pse.trackstate._buffer = self.d
        res = self.pse.state_work(self.d)
        self.assertIsInstance(res, list)
        self.assertTrue(self.pse._in_air)


class PrivateTrackAdapterTest(unittest.TestCase):
    def setUp(self):
        self.pta = services.PrivateTrackAdapter(track.DTYPE)

    def test_interface(self):
        verifyObject(ITrackType, self.pta)
