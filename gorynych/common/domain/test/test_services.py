import unittest

import mock

from gorynych.common.domain.services import times_from_checkpoints
from gorynych.common.exceptions import BadCheckpoint
from info.domain.test.helpers import create_checkpoints


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
