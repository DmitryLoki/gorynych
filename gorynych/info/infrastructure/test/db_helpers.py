'''
Helpers for tests: DB initialization etc.
'''
__author__ = 'Boris Tsema'

from txpostgres import txpostgres
from twisted.internet import defer

from gorynych import OPTS
from gorynych.common.infrastructure import persistence as pe

POOL = txpostgres.ConnectionPool(None, host=OPTS['db']['host'],
                                 database=OPTS['db']['database'],
                                 user=OPTS['db']['user'],
                                 password=OPTS['db']['password'],
                                 min=10)


@defer.inlineCallbacks
def initDB(aggregate_name, pool):
    for command in pe.drop_tables(aggregate_name):
        yield pool.runOperation(command)
    for create_table in pe.create_tables(aggregate_name):
        yield pool.runOperation(create_table)


@defer.inlineCallbacks
def tearDownDB(aggregate_name, pool=POOL):
    for command in pe.drop_tables(aggregate_name):
        yield pool.runOperation(command)
