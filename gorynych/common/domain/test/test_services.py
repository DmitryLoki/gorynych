import unittest
from unittest import TestCase

import mock

from gorynych.common.domain.services import times_from_checkpoints, bearing
from gorynych.common.exceptions import BadCheckpoint
from gorynych.info.domain.test.helpers import create_checkpoints


class TestTimesFromCheckpoints(unittest.TestCase):
    def test_good_case(self):
        chs = create_checkpoints()
        self.assertTupleEqual(times_from_checkpoints(chs),
            (1347711300, 1347732000))

    def test_bad_case(self):
        ch2 = mock.Mock()
        ch2.open_time, ch2.close_time = 4, None
        self.assertRaises(BadCheckpoint, times_from_checkpoints, [ch2])


if __name__ == '__main__':
    unittest.main()


class TestBearing(TestCase):
    def test_bearing(self):
        self.assertEqual(0., bearing(60, 0, 61, 0),
            "Bearing not zero")
        self.assertEqual(0, bearing(45, 45, 45, 45),
            "Incorrect bearing calculation for equal points.")
        self.assertAlmostEqual(25.7823, bearing(60, 0, 61, 1), 2,
            "Wrong bearing")
        self.assertAlmostEqual(206.6527, bearing(61, 1, 60, 0), 2,
            "Wrong bearing")
        self.assertAlmostEqual(91.00, bearing(61, 1, 60.96056, 3.31222), 2,
            "Wrong bearing")
