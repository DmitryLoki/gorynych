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


def initDB(aggregate_name, pool):
    drop_tables = ''.join(pe.drop_tables(aggregate_name))
    d = defer.succeed(drop_tables)
    d.addCallback(pool.runOperation)

    create_tables = ''.join(pe.create(aggregate_name))
    d.addCallback(lambda _: pool.runOperation(create_tables))
    return d


def tearDownDB(aggregate_name, pool=POOL):
    drop_tables = ';'.join(pe.drop_tables(aggregate_name))
    return  pool.runOperation(drop_tables)
