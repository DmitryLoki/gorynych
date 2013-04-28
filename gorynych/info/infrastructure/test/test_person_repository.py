'''
Created on 24.04.2013

@author: licvidator
'''
from datetime import datetime
import os

import mock
from txpostgres import txpostgres
from twisted.trial import unittest
from twisted.internet import defer, reactor

from gorynych.info.infrastructure import PGSQLPersonRepository
# TODO: create separate module with test utils
from gorynych.info.domain.test.test_person import create_person
from gorynych.info.domain.person import Person, PersonID
from gorynych import OPTS

SQL_FILE = os.path.join(os.path.dirname(__file__), 'createdb.sql')

def initDB(pool):
    def init_interaction(cur):
        sql_commands = open(SQL_FILE, 'r').read().split(';')
        d = cur.execute(sql_commands[0])
        for command in sql_commands[1:-1]:
            print '_' * 80
            print 'command is:'
            print command
            d.addCallback(lambda _ :cur.execute(command))
        return d
    return pool.runInteraction(init_interaction)


POOL = txpostgres.ConnectionPool(None, host=OPTS['db']['host'],
                                 database=OPTS['db']['database'],
                                 user=OPTS['db']['user'],
                                 password=OPTS['db']['password'],
                                 min=10)

class Test(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        yield POOL.start()
        yield initDB(POOL)
        self.repo = PGSQLPersonRepository.PGSQLPersonRepository(POOL)

    @defer.inlineCallbacks
    def tearDown(self):
        yield POOL.close()

    @defer.inlineCallbacks
    def test_get_by_id(self):
        p_id = PersonID()
        date = datetime.now()
        ret = yield POOL.runQuery(PGSQLPersonRepository.SQL_INSERT_PERSON, 
                        ('lname', 'fname', date, 'ru', 'a@a.ru', str(p_id) ))
        saved_pers = yield self.repo.get_by_id(p_id)
        self.assertIsNotNone(saved_pers)
        self.assertTupleEqual(('Fname Lname', 'RU', str(p_id)),
            (saved_pers.name.full(), saved_pers.country, str(saved_pers.id))) 

    @defer.inlineCallbacks
    def test_save_new(self):
        pers = create_person()
        saved_pers = yield self.repo.save(pers)
        self.assertEqual(pers, saved_pers, 'Something strange happens while saving')
        self.assertIsNotNone(saved_pers._id)
        db_row = yield POOL.runQuery(PGSQLPersonRepository.SQL_SELECT_PERSON, 
                                     (str(pers.id),))
        self.assertEqual(len(db_row), 1)
        db_row = db_row[0]
        self.assertTupleEqual(('John', 'Doe', 'UA', str(pers.id)), 
                              (db_row[0], db_row[1], db_row[2], db_row[5]))
        
    @defer.inlineCallbacks
    def test_update_existing(self):
        p_id = PersonID()
        date = datetime.now()
        yield POOL.runOperation(PGSQLPersonRepository.SQL_INSERT_PERSON, 
                        'lname', 'fname', date, 'ru', 'a@a.ru', str(p_id) )
        try:
            saved_pers = yield self.repo.get_by_id(p_id)
        except Exception:
            raise unittest.SkipTest("Can't test becaues get_by_id isn't working.")
        if not saved_pers:
            raise unittest.SkipTest("Got null instead of Person.")
        
        saved_pers.country = 'USA'
        saved_pers.name = {'name': 'John'}
        s = yield self.repo.save(saved_pers)
        db_row = yield POOL.runQuery(PGSQLPersonRepository.SQL_SELECT_PERSON, 
                                     (str(p_id,)))
        self.assertTupleEqual(('John', 'US'), (db_row[0][0], db_row[0][2]))
        
        
        
        
        

if __name__ == "__main__":
    unittest.main()
