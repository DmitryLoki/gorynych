#! /usr/bin/python
#coding=utf-8
from twisted.internet import defer

from zope.interface.declarations import implements
from gorynych.info.domain.person import PersonFactory, IPersonRepository
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_PERSON = """
SELECT
LASTNAME
, FIRSTNAME
, COUNTRY
, EMAIL
, REGDATE
, PERSON_ID
, ID
 FROM PERSON
 WHERE ID = %s
"""

SQL_INSERT_PERSON = """
INSERT INTO PERSON(
 LASTNAME
, FIRSTNAME
, REGDATE
, COUNTRY
, EMAIL
, PERSON_ID
)VALUES(%s, %s, %s, %s, %s, %s)
 RETURNING ID
"""

SQL_UPDATE_PERSON = """
UPDATE PERSON SET
 LASTNAME = %s
, FIRSTNAME = %s
, REGDATE = %s
, COUNTRY = %s
, EMAIL = %s
 WHERE PERSON_ID = %s
"""


class PGSQLPersonRepository(object):
    implements(IPersonRepository)

    def __init__(self, pool):
        self.pool = pool
        # Пока пусть там будет никакое значение -
        # всё равно от event_publisher'а отказываемся
        self.factory = PersonFactory(1)

    @defer.inlineCallbacks
    def get_by_id(self, person_id):
        data = yield self.pool.runQuery(SQL_SELECT_PERSON, (person_id,))
        if not data:
            raise NoAggregate("Person")
        result = self._create_person(data[0])

#        tracks_data = yield self.pool.runQuery(SQL_GET_PERSON_TRACKS.format(
#        tracks_table=TRACKS_TABLE), (person_id,))
#        result = self._insert_tracks(result, tracks_data)
        defer.returnValue(result)

    def _create_person(self, data_row):
        if data_row:
            # regdate is datetime.datetime object
            regdate = data_row[4]
            result = self.factory.create_person(
                data_row[0],
                data_row[1],
                data_row[2],
                data_row[3],
                regdate.year,
                regdate.month,
                regdate.day,
                data_row[5])
            result._id = data_row[6]
            return result

#    def _insert_tracks(self, person, tracks):
#        # Not ready yet.
#        return person

#    @defer.inlineCallbacks
#    def get_list(self, limit=None, offset=0):
#        # TODO: limit and offset
#        pers_list = yield self.pool.runQuery(SQL_GET_PERSON_LIST.format(
#                        person_table=PERSON_TABLE))
#        result = []
#        for pers in pers_list:
#            pers = self._create_person(pers)
#            if pers:
#                result.append(pers)
#        defer.returnValue(result)

    def save(self, pers):
        d = None
        if pers._id:
            d = self.pool.runOperation(SQL_UPDATE_PERSON,
                                       self._extract_sql_fields(pers))
            d.addCallback(lambda _: pers)
        else:
            d = self.pool.runQuery(SQL_INSERT_PERSON,
                                   self._extract_sql_fields(pers))
            d.addCallback(self._process_insert_result, pers)
        return d

    def _extract_sql_fields(self, pers=None):
        if pers is None:
            return ()
        return (pers.name.surname(), pers.name.name(), pers.regdate,
                    pers.country.code(), pers.email, str(pers.id))

    def _process_insert_result(self, data, pers):
        if data is not None and pers is not None:
            inserted_id = data[0][0]
            pers._id = inserted_id
            return pers
        return None
