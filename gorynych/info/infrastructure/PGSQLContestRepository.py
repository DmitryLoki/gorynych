from zope.interface.declarations import implements
from gorynych.info.domain.contest import ContestFactory, IContestRepository
from gorynych.common.exceptions import NoAggregate

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


class PGSQLContestRepository(object):
    implements(IContestRepository)

# Передаем ConnectionPool, с которым будет работать репозиторий
    def __init__(self, pool):
        self.pool = pool

# Выполняем SQL_SELECT_CONTEST с передачей contest_id, возвращаем deferred
    def get_by_id(self, contest_id):
        d = self.pool.runQuery(SQL_SELECT_CONTEST, (contest_id,))
# По завершению запроса вызываем parse_select_result
        d.addBoth(self.parse_select_result)
        return d

    def parse_select_result(self, data):
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
        return NoAggregate("Contest")

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
        if data is not None:
            inserted_id = data[0][0]
            value.id = inserted_id
            return value
        return None

    def _params(self, value=None, with_id=False):
        if value is None:
            return ()
        if with_id:
            return (value.title, value.start_time, value.end_time,
                    value.address.place, value.address.country,
                    value.address.lat, value.address.lon, value.id)
        return (value.title, value.start_time, value.end_time,
                value.address.place, value.address.country,
                value.address.lat, value.address.lon)
