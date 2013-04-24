'''
Created on 24.04.2013

@author: licvidator
'''
import unittest
from twisted.internet import defer
from gorynych.info.infrastructure.persistence import ConnectionManager
# from gorynych.info.infrastructure.PGSQLPersonRepository import PGSQLPersonRepository


class Test(unittest.TestCase):

    def setUp(self):
#         self.manager = ConnectionManager()
#         self.pool = self.manager.pool()
#         wfd = defer.waitForDeferred(self.pool.start())
#         yield wfd
#         pool = wfd.result()
#         print pool
#        self.rep = PGSQLPersonRepository(self.pool)
        pass

    def tearDown(self):
#         self.rep = None
#         self.pool.close()
        pass

    def test_get_by_id(self):
#        d = self.rep.get_by_id(0)
#        d.addCallback(self.get_by_id_success)
        pass

    def get_by_id_success(self, value):
        print "value: %s" % (value)
        pass

    def test_save(self):
        pass

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
