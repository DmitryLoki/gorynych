import unittest
from unittest import TestCase

import mock

from gorynych.common.domain.services import times_from_checkpoints, bearing, SinglePollerService
from gorynych.common.exceptions import BadCheckpoint
from gorynych.info.domain.test.helpers import create_checkpoints
from gorynych.common.infrastructure.messaging import FakeRabbitMQObject, RabbitMQObject


class TestTimesFromCheckpoints(unittest.TestCase):
    def test_good_case(self):
        chs = create_checkpoints()
        self.assertTupleEqual(times_from_checkpoints(chs),
            (1347711300, 1347732000))

    def test_bad_case(self):
        ch2 = mock.Mock()
        ch2.open_time, ch2.close_time = 4, None
        self.assertRaises(BadCheckpoint, times_from_checkpoints, [ch2])


class TestSinglePollerService(unittest.TestCase):

    def _sample_connection(self):
        return FakeRabbitMQObject(RabbitMQObject)

    def test_good_start(self):
        con = self._sample_connection()
        poller = SinglePollerService(con, 0, queue_name='some_name')
        poller.poll = mock.MagicMock()
        poller.startService()
        poller.poll.assert_any_call(queue_name='some_name')

    def test_data_access(self):
        con = self._sample_connection()
        poller = SinglePollerService(con, 0, queue_name='some_name')
        con.write('Hi!')

        def runner_poll(**kwargs):
            """
            Special test method to run handle_payload after poll
            """
            d = poller.connection.read(**kwargs)
            d.addCallback(lambda data: poller.handle_payload(*data, **kwargs))
            d.callback('go!')
            return d

        poller.poll = runner_poll
        poller.handle_payload = mock.MagicMock()
        poller.startService()
        poller.handle_payload.assert_called_with('Hi!', 'test_param', queue_name='some_name')

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
