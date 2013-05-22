import unittest
import datetime

from gorynych.info.domain import person
from gorynych.info.domain.ids import TrackerID, ContestID, PersonID

def create_person(name='John', surname='Doe',
                  country='UA', email='johndoe@example.com', reg_year=None,
                  reg_month=None,
                  reg_day=None, id=None):
    factory = person.PersonFactory()
    pers = factory.create_person(name, surname, country, email, reg_year,
        reg_month, reg_day, id)
    return pers


class PersonFactoryTest(unittest.TestCase):
    def test_create_person(self):
        self.assertEqual(person.MINYEAR, 2012)
        pers = create_person('Harold', 'Herzen', 'DE', 'boss@gmail.com',
                             '2012', 11, '30')

        self.assertEqual(pers.name.full(), 'Harold Herzen')
        self.assertEqual(pers.country, 'DE')
        self.assertEqual(str(pers.id).split('-')[0], 'pers')
        self.assertEqual(pers.email, 'boss@gmail.com')
        self.assertEqual(pers.regdate, datetime.date(2012, 11, 30))
        self.assertIsNone(pers._id)

        another_pers = create_person('Harold', 'erzen', 'DE',
                                     'bss@gmail.com', '2012',
                                     11, '30')
        self.assertNotEqual(pers.id, another_pers.id)

    def test_create_with_id(self):
        pid = PersonID()
        pers = create_person('Harold', 'Herzen', 'DE', 'boss@gmail.com',
                             '2012', 11, '30', str(pid))
        self.assertEqual(pers.name.full(), 'Harold Herzen')
        self.assertEqual(pers.country, 'DE')
        self.assertEqual(pers.id, pid)
        self.assertEqual(pers.email, 'boss@gmail.com')
        self.assertEqual(pers.regdate, datetime.date(2012, 11, 30))
        self.assertIsNone(pers._id)

    def test_good_init_without_regdate(self):
        self.assertEqual(person.MINYEAR, 2012)
        pers = create_person('Harold', 'Herzen', 'DE', 'boss@gmail.com')

        self.assertEqual(pers.name.full(), 'Harold Herzen')
        self.assertEqual(pers.country, 'DE')
        self.assertEqual(str(pers.id).split('-')[0], 'pers')
        self.assertEqual(pers.regdate, datetime.date.today())

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
        tracker_id = TrackerID()
        self.person.assign_tracker(tracker_id)
        self.assertEqual(self.person.tracker, tracker_id)

    def test_tracker_unassignment(self):
        tracker_id = TrackerID()
        another_tracker = TrackerID()
        self.person.assign_tracker(tracker_id)
        self.assertRaises(KeyError, self.person.unassign_tracker,
            another_tracker)
        self.person.unassign_tracker(tracker_id)
        self.assertIsNone(self.person.tracker)

    def test_participate_in_contest(self):
        contest_id = ContestID()
        self.person.participate_in_contest(contest_id,
            'paraglider')
        self.assertTrue(contest_id in self.person.contests)
        self.assertEqual(self.person._contests[contest_id],
            'paraglider')

        self.assertRaises(ValueError, self.person.participate_in_contest,
            14, 2)

        self.person.dont_participate_in_contest(contest_id)
        self.assertFalse(contest_id in self.person.contests)

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

    def test_equality(self):
        pid = PersonID()
        p1 = create_person(id=pid)
        p2 = create_person(id=pid)
        self.assertEqual(p1, p2)


if __name__ == '__main__':
    unittest.main()
