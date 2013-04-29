#! /usr/bin/python
#coding=utf-8
from twisted.internet import defer

from zope.interface.declarations import implements
from gorynych.info.domain.contest import ContestFactory, IContestRepository
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_CONTEST = """
SELECT
 ID
, CONTEST_ID
, TITLE
, START_DATE
, END_DATE
, PLACE
, COUNTRY
, HQ_LAT
, HQ_LON
 FROM CONTEST
 WHERE ID = %s
"""

SQL_INSERT_CONTEST = """
INSERT INTO CONTEST(
 TITLE
, START_DATE
, END_DATE
, PLACE
, COUNTRY
, HQ_LAT
, HQ_LON
, CONTEST_ID
) VALUES (%s, %s, %s, %s, %s, %s, %s)
 RETURNING ID
"""

SQL_UPDATE_CONTEST = """
UPDATE CONTEST SET
 TITLE = %s
, START_DATE = %s
, END_DATE = %s
, PLACE = %s
, COUNTRY = %s
, HQ_LAT = %s
, HQ_LON = %s
WHERE CONTEST_ID = %s
"""


class PGSQLContestRepository(object):
    implements(IContestRepository)

    def __init__(self, pool):
        self.pool = pool

    def _process_select_result(self, data):
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

    def _process_insert_result(self, data, value):
        if data is not None and value is not None:
            inserted_id = data[0][0]
            value._id = inserted_id
            return value
        return None

    def _params(self, value=None):
        if value is None:
            return ()
        return (value.title, value.start_time, value.end_time,
                value.address.place, value.address.country,
                value.address.lat, value.address.lon, value.id)

    @defer.inlineCallbacks
    def get_by_id(self, contest_id):
        data = yield self.pool.runQuery(SQL_SELECT_CONTEST, (contest_id,))
        if not data:
            raise NoAggregate("Contest")
        result = self._process_select_result(data)
        defer.returnValue(result)

    def save(self, value):
        d = None
        if value.id is not None:
            d = self.pool.runOperation(SQL_UPDATE_CONTEST,
                                       self._params(value))
            d.addCallback(lambda _: value)
        else:
            d = self.pool.runQuery(SQL_INSERT_CONTEST, self._params(value))
            d.addCallback(self._process_insert_result, value)
        return d
