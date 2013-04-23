'''
Created on 24.04.2013

@author: licvidator
'''
import unittest
from gorynych.info.infrastructure.persistence import ConnectionManager


class Test(unittest.TestCase):

    def setUp(self):
        self.manager = ConnectionManager()
        self.pool = self.manager.pool()
        pass

    def tearDown(self):
        pass

    def testName(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()