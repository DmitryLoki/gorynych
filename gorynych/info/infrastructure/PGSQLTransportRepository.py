#! /usr/bin/python
#coding=utf-8
from twisted.internet import defer

from zope.interface.declarations import implements
from gorynych.info.domain.transport import ITransportRepository, TransportFactory
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_TRANSPORT = """
SELECT 
TRANSPORT_ID, 
TRANSPORT_TYPE,  
TITLE, 
DESCRIPTION 
FROM TRANSPORT 
WHERE TRANSPORT_ID = %s
"""

SQL_INSERT_TRANSPORT = """
INSERT INTO TRANSPORT (
TRANSPORT_TYPE, 
TITLE, 
DESCRIPTION 
VALUES(%s, %s, %s) 
RETURNING TRANSPORT_ID
"""

SQL_UPDATE_TRANSPORT = """
UPDATE TRANSPORT SET 
TRANSPORT_TYPE = %s, 
TITLE = %s, 
DESCRIPTION = %s 
WHERE TRANSPORT_ID = %s
"""


class PGSQLTransportRepository(object):
    implements(ITransportRepository)

    def __init__(self, pool):
        self.pool = pool

    def _process_select_result(self, data):
        if len(data) >= 1:
            data_row = data[0]
            if data_row is not None:
                factory = TransportFactory()
                result = factory.create_transport(
                    data_row[0],
                    data_row[1],
                    data_row[2],
                    data_row[3]
                )
                return result
        raise NoAggregate("Transport")

    def _process_insert_result(self, data, value):
        if data is not None and value is not None:
            inserted_id = data[0][0]
            value.id = inserted_id
            return value

    def _params(self, value=None, with_id=False):
        if value is None:
            return ()
        if with_id:
            return (value.type, value.title, value.description, value.id)
        return (value.type, value.title, value.description)

    def get_by_id(self, transport_id):
        d = self.pool.runQuery(SQL_SELECT_TRANSPORT, (transport_id,))
        d.addBoth(self._process_select_result)
        return d

    def save(self, value):
        d = None
        if value._id is not None:
            d = self.pool.runOperation(SQL_UPDATE_TRANSPORT,
                                       self._params(value, True))
            d.addCallback(lambda _: value)
        else:
            d = self.pool.runQuery(SQL_INSERT_TRANSPORT, self._params(value))
            d.addCallback(self._process_insert_result, value)
        return d
