#! /usr/bin/python
#coding=utf-8

import psycopg2  # @UnusedImport
from datetime import datetime  # @UnusedImport
from txpostgres import txpostgres
from zope.interface.interfaces import Interface
from zope.interface.declarations import implements
from twisted.internet import reactor, defer  # @UnusedImport
from twisted.python import log, util  # @UnusedImport

# ==========|SQL-КОМАНДЫ|==========

SQL_SELECT_CONTEST = "SELECT \
CONTEST_ID \
, TITLE \
, START_DATE \
, END_DATE \
, HQ_PLACE \
, HQ_COUNTRY \
, HQ_LAT \
, HQ_LON \
FROM CONTEST \
WHERE CONTEST_ID = %s\
"

SQL_INSERT_CONTEST = "INSERT INTO CONTEST( \
TITLE \
, START_DATE \
, END_DATE \
, HQ_PLACE \
, HQ_COUNTRY \
, HQ_LAT \
, HQ_LON \
) VALUES (%s, %s, %s, %s, %s, %s, %s) \
RETURNING CONTEST_ID\
"

SQL_UPDATE_CONTEST = "UPDATE CONTEST SET \
TITLE = %s \
, START_DATE = %s \
, END_DATE = %s \
, HQ_PLACE = %s \
, HQ_COUNTRY = %s \
, HQ_LAT = %s \
, HQ_LON = %s \
WHERE CONTEST_ID = %s\
"

# ==========|НУЖНО ДЛЯ РАБОТЫ ЭТОГО ТЕСТА|==========

connectionParams = {
    "server": "localhost",
    "dbname": "airtribune",
    "user": "airtribune",
    "password": "airtribune",
    "schema": "airtribune_test"
}


class ContestFactory(object):
    def __init__(self):
        pass

    def create_contest(self, contest_id, title, start_time, end_time,
                       contest_place, contest_country, hq_coords):
        print "create contest %r, %r, %r, %r, %r, %r, %r" % (contest_id, title,
            start_time, end_time, contest_place, contest_country, hq_coords)
        return Contest(id, title, start_time, end_time, contest_place,
                       contest_country, hq_coords)


class IContestRepository(Interface):
    def get_by_id(contest_id):  # @NoSelf
        '''
        '''
    def save(person):  # @NoSelf
        '''
        '''


class NoAggregate(Exception):
    pass


class Contest(object):
    def __init__(self, contest_id, title, start_time, end_time,
                 contest_place, contest_country, hq_coords):
        self.id = contest_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.contest_place = contest_place
        self.contest_country = contest_country
        self.hq_coords = hq_coords


# ==========|АСИНХРОННАЯ ОБВЯЗКА|==========
# Контекст выполнения асинхронных вызовов
class AsyncContext(object):
    def __init__(self):
        # Ссылка на само соединение
        self.connection = None
        # Ссылка на курсор (не факт что понадобится)
        self.cursor = None
        # Функция, вызываемая после успешного выполнения Executor-а
        self.callback = None
        # Данные, используемые в работе Executor-а, хранятся здесь
        self.data = dict()


# ==========|РЕПОЗИТОРИЙ|==========
class PGSQLContestRepository(object):
    implements(IContestRepository)

    def __init__(self, pool):
        self.pool = pool

    def get_by_id(self, contest_id):
        d = self.pool.runQuery(SQL_SELECT_CONTEST, (contest_id,))
        d.addCallback(self.parse_select_result)
        return d

    def parse_select_result(self, data):
        print "data: " % (data,)
        if len(data) == 1:
            data_row = data[0]
            factory = ContestFactory()
            result = factory.create_contest(
                data_row[0],
                data_row[1],
                data_row[2],
                data_row[3],
                data_row[4],
                data_row[5],
                [data_row[6], data_row[7]]
            )
            return result
        return None

    def _params(self, value=None, with_id=False):
        if value is None:
            return ()
        if with_id:
            return (value.title, value.start_time, value.end_time,
                    value.contest_place, value.contest_country,
                    value.hq_coords[0], value.hq_coords[1], value.id)
        return (value.title, value.start_time, value.end_time,
                value.contest_place, value.contest_country, value.hq_coords[0],
                value.hq_coords[1])

    def save(self, value):
        d = None
        if value.id is not None:
            d = self.pool.runOperation(SQL_UPDATE_CONTEST,
                                       self._params(value, True))
            d.addCallback(lambda _: value)
        else:
            d = self.pool.runQuery(SQL_INSERT_CONTEST, self._params(value))
            d.addCallback(self.process_insert_id, value)
        return d

    def process_insert_id(self, data, value):
        print "process_insert_id: %r, %r" % (data, value)
        if data is not None:
            inserted_id = data[0][0]
            value.id = inserted_id
            print "returning value"
            return value
        print "returning none"
        return None

    def _close_connection(self, context):
        context.connection.close()
        return context
# ==========|ЗАПУСК ТЕСТА|==========


def run_test():
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
    d1 = rep.get_by_id(10000)
    d1.addCallback(load_ok)
    for i in xrange(10):
        d1 = rep.get_by_id(i)
        d1.addCallback(load_ok)

    data_collector = []
    for i in xrange(10):
        value = Contest(None, "TEST VALUE 01", datetime.now(), datetime.now(),
                         "TEST VALUE02", "TEST VALUE 03", [20, 30])
        d2 = rep.save(value)
        d2.addCallback(save_ok, data_collector)


def load_ok(context=None):
    print "load_ok"
    print "load_ok result: %r" % (context,)


def save_ok(context=None, data_collector=[]):
    print "save_ok"
    print "save_ok result: %r, %r" % (context, data_collector)


if __name__ == "__main__":
    reactor.callLater(0, run_test)  # @UndefinedVariable
    print "Starting reactor"
    reactor.run()  # @UndefinedVariable
