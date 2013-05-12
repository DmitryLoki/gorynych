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
    drop_tables = ';'.join(pe.drop_tables(aggregate_name))
    yield pool.runOperation(drop_tables)

    create_tables = ';'.join(pe.create_tables(aggregate_name))
    yield pool.runOperation(create_tables)


@defer.inlineCallbacks
def tearDownDB(aggregate_name, pool=POOL):
    drop_tables = ';'.join(pe.drop_tables(aggregate_name))
    yield pool.runOperation(drop_tables)
