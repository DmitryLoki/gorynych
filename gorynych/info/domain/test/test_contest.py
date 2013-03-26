import unittest

import mock

from gorynych.info.domain import contest
from gorynych.common.domain.types import Address, Name, Country
from gorynych.info.domain.tracker import TrackerID

def create_contest(id, start_time, end_time, title='  Hello world  ',
                   place ='Yrupinsk', country='rU', coords=(45.23, -23.22)):
    factory = contest.ContestFactory(mock.MagicMock())
    cont = factory.create_contest(id, title, start_time, end_time, place,
                                                        country, coords)
    return cont

class ContestFactoryTest(unittest.TestCase):
    def test_creation(self):
        factory = contest.ContestFactory(mock.MagicMock())
        self.assertIsInstance(factory.event_publisher, mock.MagicMock)

    def test_successfull_contest_creation(self):
        cont = create_contest(contest.ContestID('ab'), 1, 2)
        self.assertIsInstance(cont.address, Address)
        self.assertEqual(cont.title, 'Hello World')
        self.assertEquals((cont.start_time, cont.end_time), (1, 2))
        self.assertIsInstance(cont.event_publisher, mock.MagicMock)
        self.assertEqual(cont.id, contest.ContestID('ab'))

        cont = create_contest('ab', 1, 3)
        self.assertEqual(cont.end_time, 3)
        self.assertEqual(cont.id, contest.ContestID('ab'))

    def test_unsuccessfull_contest_creation(self):
        self.assertRaises(ValueError, create_contest, 1, 3, 1)


if __name__ == '__main__':
    unittest.main()

class TestParaglider(unittest.TestCase):
    def test_success_creation(self):
        p = contest.Paraglider('1', Name('Vasya', 'Pupkin'),
                            Country('RU'), 'Mantra 9', 15, 16)
        self.assertEqual(p.person_id, '1')
        self.assertEqual(p.glider, 'mantra')
        self.assertEqual(p.contest_number, 15)
        self.assertEqual(p.tracker_id, TrackerID(16))
