from zope.interface.declarations import implements
from gorynych.info.domain.tracker import ITrackerRepository, TrackerFactory

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
        result = None
        factory = TrackerFactory() 
        if tracker_id in self.record_cache:
            cache_row = self.record_cache[tracker_id]
            result = factory.create_tracker(
                cache_row["TRACKER_ID"], 
                cache_row["DEVICE_ID"],
                cache_row["DEVICE_TYPE"],
                cache_row["NAME"])
        else:
            if self.connection is not None:
                cursor = self.connection.cursor()
                cursor.execute(SQL_SELECT_TRACKER, (tracker_id, ))
                data_row = cursor.fetchone()
                self.copy_from_data_row(data_row)
                result = factory.create_tracker(
                    data_row[0],
                    data_row[1],
                    data_row[2],
                    data_row[3],
                )
        return result

    def save(self, value):
        if self.connection is not None:
            cursor = self.connection.cursor()
            if value.tracker_id is None:
                cursor.execute(SQL_INSERT_TRACKER, self.params(value))
                data_row = cursor.fetchone()
                if data_row is not None:
                    value.tracker_id = data_row[0]
            else:
                cursor.execute(SQL_UPDATE_TRACKER, self.params(value, True))
        self.copy_from_value(value)
        
    def copy_from_value(self, value):
        if value is None:
            return
        if value.tracker_id is None:
            return
        if value.tracker_id in self.record_cache:
            cache_row = self.record_cache[value.tracker_id]
        else:
            cache_row = dict()
        cache_row["TRACKER_ID"] = value.tracker_id
        cache_row["DEVICE_ID"] = value.device_id
        cache_row["DEVICE_TYPE"] = value.device_type
        cache_row["NAME"] = value._name
        self.record_cache[value.tracker_id] = cache_row
    
    def copy_from_data_row(self, data_row):
        if data_row[0] in self.record_cache:
            cache_row = self.record_cache[data_row[0]]
        else:
            cache_row = dict()
        cache_row["TRACKER_ID"] = data_row[0]
        cache_row["DEVICE_ID"] = data_row[1]
        cache_row["DEVICE_TYPE"] = data_row[2]
        cache_row["NAME"] = data_row[3]
        self.record_cache[data_row[0]] = cache_row
    
    def params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.device_id, value.device_type, value._name, value.tracker_id)
        return (value.device_id, value.device_type, value._name)
