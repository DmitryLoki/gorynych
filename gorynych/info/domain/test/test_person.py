import unittest
import datetime

import mock

from gorynych.info.domain import person

def create_person(name, surname, country, email, reg_year, reg_month,
                  reg_day, event_publisher=None):
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


if __name__ == '__main__':
    unittest.main()
