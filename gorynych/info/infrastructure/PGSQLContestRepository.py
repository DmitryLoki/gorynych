from zope.interface.declarations import implements
from gorynych.info.domain.contest import ContestFactory, IContestRepository

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
        factory = ContestFactory()
        if contest_id in self.record_cache:
            cache_row = self.record_cache[contest_id]
            title = cache_row["TITLE"]
            start_date = cache_row["START_DATE"]
            end_date = cache_row["END_DATE"]
            place = cache_row["START_DATE"]
            country = cache_row["COUNTRY"]
            coords = cache_row["HQ_COORDS"]

            result = factory.create_contest(contest_id, title, start_date, end_date, place, country, coords)
            return result
        # if record is not in cache - then load record from DB
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(SQL_SELECT_CONTEST, (contest_id,))
            data_row = cursor.fetchone()
            if data_row is not None:
                # store to cache
                self.copy_from_data_row(data_row)

                # build Contest object from our data
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

    def save(self, value):
        if self.connection is not None:
            cursor = self.connection.cursor()
            # no contest_id, insert new record
            if value.id is None:
                cursor.execute(SQL_INSERT_CONTEST, self.params(value))
                data_row = cursor.fetchone()
                if data_row is not None:
                    value.id = data_row[0]
            else:
                cursor.execute(SQL_UPDATE_CONTEST, self.params(value, True))
        self.copy_from_value(value)

    def copy_from_value(self, value):
        if value is None:
            return
        if value.id is None:
            return
        if value.id in self.record_cache:
            cache_row = self.record_cache[value.id]
        else:
            cache_row = dict()
        cache_row["CONTEST_ID"] = value.id
        cache_row["TITLE"] = value.title
        cache_row["TITLE"] = value.title
        cache_row["START_DATE"] = value.start_time
        cache_row["END_DATE"] = value.end_time
        if value.address is not None:
            cache_row["HQ_PLACE"] = value.address.place
            cache_row["HQ_COUNTRY"] = value.address.country
            cache_row["HQ_COORDS"] = [value.address.lat, self.address.lon]

    def copy_from_data_row(self, data_row):
        if data_row is None:
            return
        if data_row[0] is None:
            return
        if data_row[0] in self.record_cache:
            cache_row = self.record_cache[data_row[0]]
        else:
            cache_row = dict()
            
        cache_row["CONTEST_ID"] = data_row[0]
        cache_row["TITLE"] = data_row[1]
        cache_row["START_DATE"] = data_row[2]
        cache_row["END_DATE"] = data_row[3]
        cache_row["HQ_PLACE"] = data_row[4]
        cache_row["HQ_COUNTRY"] = data_row[5]
        cache_row["HQ_COORDS"] = [data_row[6], data_row[7]]
        self.record_cache[data_row[0]] = cache_row

    def params(self, value = None, with_id = False):
        if value is None:
            return (value.title, value.start_time, value.end_time, value.address.place, 
                    value.address.country, value.address.lat, value.address.lon)
        if with_id:
            return (value.title, value.start_time, value.end_time, value.address.place, 
                    value.address.country, value.address.lat, value.address.lon, value.id)
        return ()