'''
Test PostgreSQL implementation of IPersonRepository.
'''
__author__ = 'Boris Tsema'
from datetime import datetime

from twisted.trial import unittest
from twisted.internet import defer

from gorynych.info.infrastructure import PGSQLPersonRepository
# TODO: create separate module with test utils
from gorynych.info.domain.test.test_person import create_person
from gorynych.info.domain.person import PersonID
from gorynych.info.infrastructure.test import db_helpers
from gorynych.common.exceptions import NoAggregate
from gorynych.common.infrastructure import persistence as pe


POOL = db_helpers.POOL


class Test(unittest.TestCase):

    def setUp(self):
        self.repo = PGSQLPersonRepository.PGSQLPersonRepository(POOL)
        d = POOL.start()
        d.addCallback(lambda _:db_helpers.initDB('person', POOL))
        return d

    def tearDown(self):
        d = db_helpers.tearDownDB('person', POOL)
        d.addCallback(lambda _:POOL.close())
        return d

    @defer.inlineCallbacks
    def test_save_new(self):
        pers = create_person()
        saved_pers = yield self.repo.save(pers)
        self.assertEqual(pers, saved_pers,
                         'Something strange happend while saving.')
        self.assertIsNotNone(saved_pers._id)
        db_row = yield POOL.runQuery(pe.select('person'), (str(pers.id),))
        self.assertEqual(len(db_row), 1)
        db_row = db_row[0]
        self.assertTupleEqual(('John', 'Doe', 'UA', str(pers.id)),
                              (db_row[0], db_row[1], db_row[2], db_row[5]))

    @defer.inlineCallbacks
    def test_get_by_id(self):
        p_id = PersonID()
        date = datetime.now()
        p__id = yield POOL.runQuery(pe.insert('person'),
                        ('name', 'surname', date, 'ru', 'a@a.ru', str(p_id) ))
        saved_pers = yield self.repo.get_by_id(p_id)
        self.assertIsNotNone(saved_pers)
        self.assertTupleEqual(('Name Surname', 'RU', str(p_id)),
            (saved_pers.name.full(), saved_pers.country, str(saved_pers.id)))
        self.assertEqual(p__id[0][0], saved_pers._id)

    @defer.inlineCallbacks
    def test_get_by_nonexistent_id(self):
        p_id = "No such id"
        yield self.assertFailure(self.repo.get_by_id(p_id), NoAggregate)

    @defer.inlineCallbacks
    def test_update_existing(self):
        p_id = PersonID()
        date = datetime.now()
        yield POOL.runOperation(pe.insert('person'),
                        ('name', 'Surname', date, 'ru', 'a@a.ru', str(p_id) ))
        try:
            saved_pers = yield self.repo.get_by_id(p_id)
        except Exception:
            raise unittest.SkipTest(
                "Can't test because get_by_id isn't working.")
        if not saved_pers:
            raise unittest.SkipTest("Got nothing instead of Person.")
        
        saved_pers.country = 'USA'
        saved_pers.name = {'name': 'asfa'}
        s = yield self.repo.save(saved_pers)
        db_row = yield POOL.runQuery(pe.select('person'), (str(p_id),))
        self.assertTupleEqual(('Asfa', 'US'), (db_row[0][0], db_row[0][2]))
        
