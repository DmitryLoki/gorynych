'''
Created on 24.04.2013

@author: licvidator
'''
import unittest
from twisted.internet import defer, reactor
from gorynych.info.infrastructure.persistence import ConnectionManager


class Test(unittest.TestCase):

    def setUp(self):
        self.manager = ConnectionManager()
        self.pool = self.manager.pool()
        wfd = defer.waitForDeferred(self.pool.start())
        yield wfd
        pool = wfd.result()
        print pool

    def tearDown(self):
        self.pool.close()
        pass

    def testName(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
