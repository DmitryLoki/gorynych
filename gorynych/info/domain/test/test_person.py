import unittest
import datetime

import mock

from gorynych.info.domain import person
from gorynych.info.domain.tracker import TrackerID

def create_person(name='John', surname='Doe',
                  country='UA', email='johndoe@example.com', reg_year=2012,
                  reg_month=4,
                  reg_day=1, event_publisher=None):
    if not event_publisher:
        event_publisher = mock.MagicMock()
    factory = person.PersonFactory(event_publisher)
    pers = factory.create_person(name, surname, country, email, reg_year,
        reg_month, reg_day)
    return pers


class PersonFactoryTest(unittest.TestCase):
    def test_good_init(self):
        self.assertEqual(person.MINYEAR, 2012)
        pers = create_person('Harold', 'Herzen', 'DE', 'boss@gmail.com', 2012,
            11, 30)

        self.assertEqual(pers.name, 'Harold Herzen')
        self.assertEqual(pers.country, 'DE')
        self.assertEqual(pers.id, 'boss@gmail.com')
        self.assertEqual(pers.regdate, datetime.date(2012, 11, 30))
        self.assertIsInstance(pers.event_publisher, mock.MagicMock)

    def test_bad_init(self):
        self.assertRaises(ValueError, create_person, 'Harold', 'Herzen',
            'DE', 'boss@gmail.com', 2010, 11, 30)
        self.assertRaises(ValueError, create_person, 'Harold', 'Herzen',
            'DE', 's@mail.ru', 2015, 11, 30)


class PersonTest(unittest.TestCase):
    def setUp(self):
        self.person = create_person()

    def test_tracker_assignment(self):
        self.person.assign_tracker(TrackerID(15))
        self.assertTrue(TrackerID(15) in self.person.trackers)
        self.assertFalse(TrackerID(16) in self.person.trackers)

    def test_tracker_unassignment(self):
        self.person.assign_tracker(TrackerID(15))
        self.assertRaises(KeyError, self.person.unassign_tracker,
            TrackerID(16))
        self.person.unassign_tracker(TrackerID(15))
        self.assertFalse(TrackerID(15) in self.person.trackers)

if __name__ == '__main__':
    unittest.main()
