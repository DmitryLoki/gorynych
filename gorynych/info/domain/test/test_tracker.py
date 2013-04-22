import unittest
import mock

from gorynych.info.domain.tracker import Tracker, TrackerHasOwner, TrackerAssigned, TrackerUnAssigned
from gorynych.info.domain.tracker import TrackerID, TrackerFactory, TrackerDontHasOwner


def create_tracker(id, device_id, device_type, event_publisher=None):
    if not event_publisher:
        event_publisher = mock.MagicMock()
    factory = TrackerFactory(event_publisher)
    tracker = factory.create_tracker(id, device_id, device_type)
    return tracker


class TrackerFactoryTest(unittest.TestCase):
    def setUp(self):
        self.skipTest("Tracker is not number one priority.")
    def test_int_creation(self):
        tracker = create_tracker(1, 'device_id', 'tr203')
        self.assertIsInstance(tracker, Tracker)
        self.assertEqual(tracker.id, 1)
        self.assertEqual(tracker.assignee, None)
        self.assertTrue(tracker.is_free())
        self.assertIsInstance(tracker.event_publisher, mock.MagicMock)

    def test_trackerid_creation(self):
        tracker = create_tracker(TrackerID(1), 'device_id', 'tr203')
        self.assertIsInstance(tracker, Tracker)
        self.assertEqual(tracker.id, 1)
        self.assertEqual(tracker.assignee, None)
        self.assertTrue(tracker.is_free())
        self.assertIsInstance(tracker.event_publisher, mock.MagicMock)


class TrackerTest(unittest.TestCase):

    def setUp(self):
        self.skipTest("Tracker is not number one priority.")
        self.id = TrackerID(2)
        self.tracker = create_tracker(self.id, 'device_id', 'tr203')

    def tearDown(self):
        del self.tracker

    def test_tracker_assignment(self):
        person_id = 'some_person'

        def set_assignee(ass):
            self.tracker.assignee = ass
        self.assertRaises(AttributeError, set_assignee, 5)
        self.assertTrue(self.tracker.is_free())

        self.tracker.assign_to(person_id)
        self.assertFalse(self.tracker.is_free())
        self.tracker.event_publisher.publish.assert_called_once_with(
                        TrackerAssigned(person_id, self.id))

        self.assertEqual(self.tracker.assignee, person_id)
        self.assertRaises(TrackerHasOwner, self.tracker.assign_to,
            'another_person')

    def test_tracker_unassignment(self):
        self.assertRaises(TrackerDontHasOwner, self.tracker.unassign)
        self.tracker.assign_to('some_person')
        self.tracker.unassign()
        self.assertTrue(self.tracker.is_free())
        self.assertTrue(self.tracker.event_publisher.mock_calls[-1] ==
                mock.call.publish(TrackerUnAssigned('some_person', self.id)))

    def test_name(self):
        self.assertEqual('', self.tracker.name)
        self.tracker.name = 'tracker_name'
        self.assertEqual(self.tracker.name, 'tracker_name')
        def set_name(name):
            self.tracker.name = name
        self.assertRaises(TypeError, set_name, 1)



class TrackerIDTest(unittest.TestCase):
    def setUp(self):
        self.skipTest("Tracker is not number one priority.")
    def test_int(self):
        t_id = TrackerID(1)
        self.assertEqual(1, t_id)

    def test_str(self):
        t_str = TrackerID('hello')
        self.assertEqual('hello', t_str)


if __name__ == '__main__':
    unittest.main()
