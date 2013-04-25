from zope.interface.declarations import implements
from gorynych.info.domain.race import IRaceRepository, Race
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_RACE = "SELECT RACE_ID, TITLE, START_TIME, FINISH_TIME FROM RACE \
WHERE RACE_ID = %s"
SQL_INSERT_RACE = "INSERT INTO RACE (TITLE, START_TIME, FINISH_TIME) \
VALUES (%s, %s, %s) RETURNING RACE_ID"
SQL_UPDATE_RACE = "UPDATE RACE SET TITLE = %s, START_TIME = %s, \
END_TIME = %s WHERE RACE_ID = %s"


class PGSQLRaceRepository(object):
    implements(IRaceRepository)

    def __init__(self, pool):
        self.pool = pool

    def _process_select_result(self, data):
        if len(data) >= 1:
            data_row = data[0]
            if data_row is not None:
                result = Race(
                    data_row[0],
                    data_row[1],
                    data_row[2],
                    data_row[3]
                )
                return result
        raise NoAggregate("Race")

    def _process_insert_result(self, data, value):
        if data is not None and value is not None:
            inserted_id = data[0][0]
            value.id = inserted_id
            return value

    def _params(self, value=None, with_id=False):
        if value is None:
            return ()
        if with_id:
            return (value.title, value.timelimits[0], value.timelimits[1],
                    value.id)
        return (value.title, value.timelimits[0], value.timelimits[1])

    def get_by_id(self, race_id):
        d = self.pool.runQuery(SQL_SELECT_RACE, (race_id,))
        d.addBoth(self._process_select_result)
        return d

    def save(self, value):
        d = None
        if value._id is not None:
            d = self.pool.runOperation(SQL_UPDATE_RACE,
                                       self._params(value, True))
            d.addCallback(lambda _: value)
        else:
            d = self.pool.runQuery(SQL_INSERT_RACE, self._params(value))
            d.addCallback(self._process_insert_result, value)
        return d
