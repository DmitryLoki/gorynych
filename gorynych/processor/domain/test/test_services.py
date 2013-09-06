import unittest
import time

import numpy as np
import mock
from shapely.geometry import Point

from gorynych.processor.domain import services
from gorynych.common.domain.types import Checkpoint


class TestOfflineCorrectorService(unittest.TestCase):
    def setUp(self):
        self.dtype = [('id', 'i4'), ('timestamp', 'i4'), ('lon', 'f4')]
        self.oc = services.OfflineCorrectorService()
        shape = 15
        ar = np.empty(shape, dtype=self.dtype)
        ar['id'] = np.arange(10, shape+10)
        ar['timestamp'] = np.arange(10, shape+10)
        ar['lon'] = np.ones(shape)
        self.ar = ar

    def tearDown(self):
        del self.ar

    def test_clean_timestamp(self):
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


class TestOnlineTrashAdapter(unittest.TestCase):
    def setUp(self):
        self.ta = services.OnlineTrashAdapter(1)
        self.dtype = [('timestamp', 'i4'), ('lat', 'f4')]
        self.ts = mock.Mock()
        _buffer = np.ones(10, self.dtype)
        self.ts._buffer = _buffer

    def tearDown(self):
        del self.ts
        del self.ta

    def test_delete(self):
        now = int(time.time())
        data = np.ones(1, self.dtype)
        data['timestamp'] = now
        self.ts._buffer['timestamp'] = np.ones(10) * now - np.arange(60, 70)
        points, evs = self.ta.process(data, 1, 2, self.ts)
        self.assertEqual(len(points), 9)
        self.assertEqual(len(self.ts._buffer), 2)


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
