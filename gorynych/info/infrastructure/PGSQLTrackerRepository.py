from zope.interface.declarations import implements
from gorynych.info.domain.tracker import ITrackerRepository, TrackerFactory
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_TRACKER = "SELECT TRACKER_ID, DEVICE_ID, DEVICE_TYPE, NAME \
FROM TRACKER WHERE TRACKER_ID = %s"
SQL_INSERT_TRACKER = "INSERT INTO TRACKER(DEVICE_ID, DEVICE_TYPE, NAME) \
VALUES (%s, %s, %s) RETURNING TRACKER_ID"
SQL_UPDATE_TRACKER = "UPDATE TRACKER SET DEVICE_ID = %s, DEVICE_TYPE = %s, \
NAME = %s WHERE TRACKER_ID = %s"

class PGSQLTrackerRepository(object):
    implements(ITrackerRepository)

    def __init__(self, connection = None):
        self.record_cache = dict()
        self.set_connection(connection)
    
    def set_connection(self, connection):
        self.connection = connection

    def get_by_id(self, tracker_id):
        if tracker_id in self.record_cache:
            return self.record_cache[tracker_id]
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(SQL_SELECT_TRACKER, (tracker_id, ))
            data_row = cursor.fetchone()
            if data_row is not None:
                factory = TrackerFactory() 
                result = factory.create_tracker(
                    data_row[0],
                    data_row[1],
                    data_row[2],
                    data_row[3],
                )
                self.record_cache[data_row[0]] = result
                return result
        raise NoAggregate("Tracker")

    def save(self, value):
        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                if value.tracker_id is None:
                    cursor.execute(SQL_INSERT_TRACKER, self.params(value))
                    data_row = cursor.fetchone()
                    if data_row is not None:
                        value.tracker_id = data_row[0]
                else:
                    cursor.execute(SQL_UPDATE_TRACKER, self.params(value, True))
            self.record_cache[value.tracker_id] = value
            return value
        except Exception:
            return None
        
    def params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.device_id, value.device_type, value._name, value.tracker_id)
        return (value.device_id, value.device_type, value._name)
