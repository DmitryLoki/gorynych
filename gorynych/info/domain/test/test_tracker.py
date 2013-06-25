import unittest
import mock

from gorynych.common.domain.events import TrackerAssigned, TrackerUnAssigned
from gorynych.info.domain.tracker import Tracker, TrackerHasOwner
from gorynych.info.domain.tracker import TrackerID, TrackerFactory, TrackerDontHasOwner


def create_tracker(id, device_id, device_type, event_publisher=None):
    if not event_publisher:
        event_publisher = mock.MagicMock()
    factory = TrackerFactory(event_publisher)
    tracker = factory.create_tracker(id, device_id, device_type)
    return tracker


class TrackerFactoryTest(unittest.TestCase):
    def test_parameters_creation(self):
        factory = TrackerFactory()
        tracker = factory.create_tracker(device_id='device_id', device_type='tr203')
        self.assertIsInstance(tracker, Tracker)
        self.assertEqual(tracker.id, 'tr203-device_id')
        self.assertEqual(tracker.device_id, 'device_id')
        self.assertEqual(tracker.device_type, 'tr203')
        self.assertEqual(tracker.assignee, None)
        self.assertEqual(tracker.name, '')
        self.assertTrue(tracker.is_free())

    def test_trackerid_creation(self):
        tid = TrackerID('tr203', '001100')
        factory = TrackerFactory()
        tracker = factory.create_tracker(tid, 'device_id', 'tr203')
        self.assertIsInstance(tracker, Tracker)
        self.assertEqual(tracker.id, 'tr203-device_id')
        self.assertEqual(tracker.device_id, 'device_id')
        self.assertEqual(tracker.device_type, 'tr203')
        self.assertEqual(tracker.assignee, None)
        self.assertTrue(tracker.is_free())


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
    def test_good(self):
        t_id = TrackerID('tr203', '00110234113423')
        self.assertIsInstance(t_id, TrackerID)
        t_id2 = TrackerID.fromstring('tr203-00110234113423')
        self.assertEqual(t_id, t_id2)
        self.assertEqual(t_id.device_id, '00110234113423')
        self.assertEqual(t_id.device_type, 'tr203')

    def test_bad(self):
        self.assertRaises(ValueError, TrackerID, 'tr20', '000')
        self.assertRaises(ValueError, TrackerID, 'tr203', '')
        self.assertRaises(ValueError, TrackerID.fromstring, 'tr203-')
        self.assertRaises(ValueError, TrackerID.fromstring, 'tr23-s')


if __name__ == '__main__':
    unittest.main()
