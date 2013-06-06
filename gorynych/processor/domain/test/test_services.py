import unittest

import numpy as np

from gorynych.processor.domain import services


class TestOfflineCorrectorService(unittest.TestCase):
    def setUp(self):
        self.dtype = [('id', 'i4'), ('timestamp', 'i4'), ('lon', 'f4')]
        self.oc = services.OfflineCorrectorService()

    def test_clean_timestamp(self):
        shape = 15
        ar = np.empty(shape, dtype=self.dtype)
        ar['id'] = np.arange(10, shape+10)
        ar['timestamp'] = np.arange(10, shape+10)
        ar['lon'] = np.ones(shape)
        ar['timestamp'][4] = ar['timestamp'][3]
        ar['timestamp'][6] = ar['timestamp'][5]-1
        result = self.oc._clean_timestamps(ar, 11, 20)
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
