'''
Created on 29.04.2013

@author: licvidator
'''
from txpostgres import txpostgres
from datetime import datetime
from twisted.internet import reactor, defer  # @UnusedImport


def run_test():
    print "starting test"
    pool = txpostgres.ConnectionPool(None,
        host="localhost", database="airtribune", user="airtribune",
        password="airtribune", min=16
    )
    d = pool.start()
    d.addCallback(connect_ok)

SQL_INSERT_TRACK_DATA = """
INSERT INTO TRACK_DATA(
  TRID
, TS
, DISTANCE
, V_SPEED
, G_SPEED
, COORD
) VALUES (%s, %s, %s, %s, %s, ST_GeometryFromText(%s, 4326))
"""


def connect_ok(pool):
    print "connect_ok"
    geometry = "POINT(%f %f)" % (10.0, 20.0)
    d1 = pool.runOperation(SQL_INSERT_TRACK_DATA, (0, datetime.now(),
                           10000, 100, 100, geometry))
    d1.addCallback(load_ok)


def load_ok(data):
    print "load_ok"
    pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    reactor.callLater(0, run_test)  # @UndefinedVariable
    print "Starting reactor"
    reactor.run()  # @UndefinedVariable
