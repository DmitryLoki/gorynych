from zope.interface.declarations import implements
from gorynych.info.domain.race import IRaceRepository, Race
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_RACE = "SELECT RACE_ID, TITLE, START_TIME, FINISH_TIME FROM RACE WHERE RACE_ID = %s"
SQL_INSERT_RACE = "INSERT INTO RACE (TITLE, START_TIME, FINISH_TIME) VALUES (%s, %s, %s) RETURNING RACE_ID"
SQL_UPDATE_RACE = "UPDATE RACE SET TITLE = %s, START_TIME = %s, END_TIME = %s WHERE RACE_ID = %s"

class PGSQLRaceRepository(object):
    implements(IRaceRepository)

    def __init__(self, connection = None):
        self.record_cache = dict()
        self.set_connection(connection)
    
    def set_connection(self, connection):
        self.connection = connection

    def get_by_id(self, race_id):
        if race_id in self.record_cache:
            return self.record_cache[race_id]
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(SQL_SELECT_RACE, (race_id,))
            data_row = cursor.fetchone()
            if data_row is not None:
                result = Race()
                result.id = data_row[0]
                result.title = data_row[1]
                result.timelimits = (data_row[2], data_row[3])
                self.record_cache[data_row[0]] = result
                return result
        raise NoAggregate("Race")

    def save(self, value):
        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                if value.id is None:
                    cursor.execute(SQL_INSERT_RACE, self.params(value))
                    data_row = cursor.fetchone()
                    if data_row is not None:
                        value.id = data_row[0]
                else:
                    cursor.execute(SQL_UPDATE_RACE, self.params(value, True))
            self.record_cache[value.id] = value
            return value
        except Exception:
            return None

    def params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.title, value.timelimits[0], value.timelimits[1], value.id)
        return (value.title, value.timelimits[0], value.timelimits[1])

