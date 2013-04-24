'''
Created on 24.04.2013

@author: licvidator
'''
import unittest
from twisted.internet import defer, reactor
from gorynych.info.infrastructure.persistence import ConnectionManager
from gorynych.info.infrastructure.PGSQLContestRepository import PGSQLContestRepository


class Test(unittest.TestCase):
    
    def setUp(self):
        # create pool and pass it to connection manager
        pass

    def tearDown(self):
        # stop pool
        pass

    def testGetById(self):
        # get item with ID 0, which is created in database via initial script
        pass

    def testSaveNew(self):
        # create new contest and save it using repository,  
        pass

    def testUpdateExisting(self):
        # create another contest, save it, change some property and save again
        pass

if __name__ == "__main__":
    unittest.main()
