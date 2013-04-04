import unittest
import datetime

import mock

from gorynych.info.domain import person
from gorynych.info.domain.tracker import TrackerID
from gorynych.info.domain.contest import ContestID

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
        pers = create_person('Harold', 'Herzen', 'DE', 'boss@gmail.com', '2012',
            11, '30')

        self.assertEqual(pers.name.full(), 'Harold Herzen')
        self.assertEqual(pers.country, 'DE')
        self.assertEqual(pers.id, 'boss@gmail.com')
        self.assertEqual(pers.regdate, datetime.date(2012, 11, 30))
        self.assertIsInstance(pers.event_publisher, mock.MagicMock)


    def test_bad_init(self):
        self.assertRaises(ValueError, create_person, 'Harold', 'Herzen',
            'DE', 'boss@gmail.com', 2010, 11, 30, "Registration date range "
                                                  "check is broken.")
        self.assertRaises(ValueError, create_person, 'Harold', 'Herzen',
            'DE', 's@mail.ru', 2015, 11, 30, "Registration date range check "
                                             "is broken.")


class PersonTest(unittest.TestCase):
    def setUp(self):
        self.person = create_person()

    def test_tracker_assignment(self):
        self.person.assign_tracker(TrackerID(15))
        self.assertEqual(self.person.tracker, TrackerID(15))

    def test_tracker_unassignment(self):
        self.person.assign_tracker(TrackerID(15))
        self.assertRaises(KeyError, self.person.unassign_tracker,
            TrackerID(16))
        self.person.unassign_tracker(TrackerID(15))
        self.assertIsNone(self.person.tracker)

    def test_participate_in_contest(self):
        self.person.participate_in_contest(ContestID('some contest'),
            'paraglider')
        self.assertTrue(ContestID('some contest') in self.person.contests)
        self.assertEqual(self.person._contests[ContestID('some contest')],
            'paraglider')

        self.assertRaises(ValueError, self.person.participate_in_contest,
            14, 2)

        self.person.dont_participate_in_contest(ContestID('some contest'))
        self.assertFalse(ContestID('some contest') in self.person.contests)

    def test_name_setter(self):
        self.person.name = dict(name='VAsya')
        self.assertEqual(self.person.name.full(), 'Vasya Doe')

        self.person.name = dict(surname=' pupkin')
        self.assertEqual(self.person.name.full(), 'Vasya Pupkin')

        self.person.name = dict(name='Nikolay', surname='vtoroy')
        self.assertEqual(self.person.name.full(), 'Nikolay Vtoroy')

    def test_country_setter(self):
        self.person.country = 'RUSSIA!'
        self.assertEqual(self.person.country, 'RU')


if __name__ == '__main__':
    unittest.main()
