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
NAME \
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
NAME = %s \
, START_DATE = %s \
, END_DATE = %s \
, HQ_PLACE = %s \
, HQ_COUNTRY = %s \
, HQ_PLACE = %s \
, HQ_LAT = %s \
, HQ_LON = %s \
WHERE CONTEST_ID = %s\
"

class PGSQLContestRepository(object):
    implements(IContestRepository)

    def __init__(self, connection):
        self.record_cache = dict()
        self.set_connection(connection)

    def set_connection(self, connection):
        self.connection = connection

    def get_by_id(self, contest_id):
        # searching in record cache
        if contest_id in self.record_cache:
            return self.record_cache[contest_id]
        # if record is not in cache - then load record from DB
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(SQL_SELECT_CONTEST, (contest_id,))
            data_row = cursor.fetchone()
            if data_row is not None:
                # build Contest object from our data
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
                self.record_cache[data_row[0]] = result
                return result
        raise NoAggregate("Contest")

    def save(self, value):
        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                if value.id is None:
                    cursor.execute(SQL_INSERT_CONTEST, self.params(value))
                    data_row = cursor.fetchone()
                    if data_row is not None:
                        value.id = data_row[0]
                else:
                    cursor.execute(SQL_UPDATE_CONTEST, self.params(value, True))
            self.record_cache[value.id] = value
            return value
        except Exception:
            return None
            

    def params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.title, value.start_time, value.end_time, value.address.place, 
                    value.address.country, value.address.lat, value.address.lon, value.id)
        return (value.title, value.start_time, value.end_time, value.address.place, 
                    value.address.country, value.address.lat, value.address.lon)