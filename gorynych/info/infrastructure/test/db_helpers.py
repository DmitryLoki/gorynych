'''
Helpers for tests: DB initialization etc.
'''
__author__ = 'Boris Tsema'

from twisted.internet import defer
from twisted.enterprise import adbapi

from gorynych import OPTS
from gorynych.common.infrastructure import persistence as pe

POOL = adbapi.ConnectionPool('psycopg2', host=OPTS['dbhost'],
    database=OPTS['dbname'], user=OPTS['dbuser'],
    password=OPTS['dbpassword'])


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
