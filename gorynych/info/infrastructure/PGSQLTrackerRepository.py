#! /usr/bin/python
#coding=utf-8
from twisted.internet import defer

from zope.interface.declarations import implements
from gorynych.info.domain.tracker import ITrackerRepository, TrackerFactory
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_TRACKER = """
SELECT  
TRACKER_ID, 
DEVICE_ID, 
DEVICE_TYPE, 
NAME, 
ASSIGNEE, 
TID
FROM TRACKER 
WHERE TRACKER_ID = %s
"""

SQL_INSERT_TRACKER = """
INSERT INTO TRACKER(
DEVICE_ID, 
DEVICE_TYPE, 
NAME,
TRACKER_ID,  
ASSIGNEE
) 
VALUES (%s, %s, %s, %s, %s) 
RETURNING TRACKER_ID
"""
SQL_UPDATE_TRACKER = """
UPDATE TRACKER SET 
DEVICE_ID = %s, 
DEVICE_TYPE = %s, 
NAME = %s, 
ASSIGNEE = %s
WHERE TRACKER_ID = %s
"""


class PGSQLTrackerRepository(object):
    implements(ITrackerRepository)

    def __init__(self, pool):
        self.pool = pool
        self.factory = TrackerFactory()

    @defer.inlineCallbacks
    def get_by_id(self, tracker_id):
        data = yield self.pool.runQuery(SQL_SELECT_TRACKER, (tracker_id,))
        if not data:
            raise NoAggregate("Tracker")
        result = self._create_tracker(data[0])
        return d

    def _create_tracker(self, data_row):
        if data_row:
            # tracker_id, device_id, device_type, name
            result = self.factory.create_tracker(
                data_row[0],
                data_row[1],
                data_row[2],
                data_row[3]
            )
            return result

    def _process_insert_result(self, data, value):
        if data is not None and value is not None:
            inserted_id = data[0][0]
            value.id = inserted_id
            return value

    def _params(self, value=None, with_id=False):
        if value is None:
            return ()
        if with_id:
            return (value.device_id, value.device_type, value._name,
                    value.tracker_id)
        return (value.device_id, value.device_type, value._name)

    def save(self, value):
        d = None
        if self.pool is not None:
            if value._id is not None:
                d = self.pool.runOperation(SQL_UPDATE_TRACKER,
                                           self._params(value, True))
                d.addCallback(lambda _: value)
            else:
                d = self.pool.runQuery(SQL_INSERT_TRACKER, self._params(value))
                d.addCallback(self._process_insert_result, value)
        return d
