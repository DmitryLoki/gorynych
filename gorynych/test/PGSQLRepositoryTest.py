#! /usr/bin/python
#coding=utf-8

import psycopg2  # @UnusedImport
from datetime import datetime  # @UnusedImport
from txpostgres import txpostgres
from twisted.internet import reactor, defer  # @UnusedImport
from twisted.python import log, util  # @UnusedImport
from gorynych.info.infrastructure.PGSQLContestRepository \
    import PGSQLContestRepository
from gorynych.info.domain.ids import ContestID, PersonID

# ==========|SQL-КОМАНДЫ|==========


def run_test():
    cid = ContestID()
    print cid
    pid = PersonID()
    print pid
    print "starting test"
    pool = txpostgres.ConnectionPool(None,
        host="localhost", database="airtribune", user="airtribune",
        password="airtribune", min=16
    )
    d = pool.start()
    d.addCallback(connect_ok)


def connect_ok(pool):
    print pool
    rep = PGSQLContestRepository(pool)
    d1 = rep.get_by_id(0)
    d1.addCallback(load_ok)


def load_ok(context=None):
    print "load_ok"
    print "load_ok result: %r" % (context,)

    print context._id
    print context.id
    print context._participants


def save_ok(context=None, data_collector=[]):
    print "save_ok"
    print "save_ok result: %r, %r" % (context, data_collector)


if __name__ == "__main__":
    reactor.callLater(0, run_test)  # @UndefinedVariable
    print "Starting reactor"
    reactor.run()  # @UndefinedVariable
