from zope.interface.declarations import implements
from gorynych.info.domain.person import PersonFactory, IPersonRepository

SQL_SELECT_PERSON = "SELECT \
PERSON_ID \
, FIRSTNAME \
, LASTNAME \
, REGDATE \
, EMAIL \
, COUNTRY \
FROM PERSON WHERE EMAIL = %s\
"
SQL_INSERT_PERSON = "INSERT INTO PERSON(\
FIRSTNAME \
, LASTNAME \
, REGDATE \
, EMAIL \
, COUNTRY \
)VALUES(%s, %s, %s, %s, %s) \
RETURNING PERSON_ID, EMAIL"

SQL_UPDATE_PERSON = "UPDATE PERSON SET \
FIRSTNAME = %s\
, LASTNAME = %s\
, REGDATE = %s\
, COUNTRY = %s \
WHERE EMAIL = %s\
"

class PGSQLPersonRepository(object):
    implements(IPersonRepository)

    def __init__(self, connection = None):
        self.record_cache = dict()
        self.set_connection(connection)

    def set_connection(self, connection):
        self.connection = connection

    def get_by_id(self, person_id):
        # searching in record cache
        # actually, as ID we use unique email address
        factory = PersonFactory()
        # create_person(name, surname, country, email, year, month, day)
        if person_id in self.record_cache:
            cache_row = self.record_cache[person_id]
            firstname = cache_row["FIRSTNAME"]
            lastname = cache_row["LASTNAME"]
            regdate = cache_row["REGDATE"]
            country = cache_row["COUNTRY"]
            email = cache_row["EMAIL"]

            result = factory.create_person(lastname, firstname, country, 
                email, regdate.year, regdate.month, regdate.day)
            return result
        # if record is not in cache - then load record from DB
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(SQL_SELECT_PERSON, (person_id,))
            data_row = cursor.fetchone()
            if data_row is not None:
                # returned_person_id = data_row[0]
                person_firstname = data_row[1]
                person_lastname = data_row[2]
                person_regdate = data_row[3]
                person_email = data_row[4]
                person_country = data_row[5]
                # copy to cache
                self.copy_from_data_row(data_row)
                # create person object from data and return result
                result = factory.create_person(
                    person_lastname, 
                    person_firstname, 
                    person_country, 
                    person_email,
                    person_regdate.year, 
                    person_regdate.month, 
                    person_regdate.day)
                return result
        return None

    def save(self, value):
        if self.connection is not None:
            cursor = self.connection.cursor()
            if value.id is None:
                cursor.execute(SQL_INSERT_PERSON, self.params(value))
                data_row = cursor.fetchone()
                if data_row is not None:
                    value.id = data_row[1]
            else:
                cursor.execute(SQL_UPDATE_PERSON, self.params(value, True))
        self.copy_from_value(value)

    def copy_from_value(self, value):
        if value is None:
            return
        if value.email is None:
            return
        if value.email in self.record_cache:
            cache_row = self.record_cache[value.email]
        else:
            cache_row = dict()
        cache_row["FIRSTNAME"] = value.name().surname()
        cache_row["LASTNAME"] = value.name().name()
        cache_row["REGDATE"] = value.regdate
        cache_row["EMAIL"] = value.id
        cache_row["COUNTRY"] = value.country().code()
        self.record_cache[value.id] = cache_row
    
    def copy_from_data_row(self, data_row):
        if data_row is None:
            return
        if data_row[4] in self.record_cache:
            cache_row = self.record_cache[data_row[4]]
        else:
            cache_row = dict()
        cache_row["FIRSTNAME"] = data_row[1]
        cache_row["LASTNAME"] = data_row[2]
        cache_row["REGDATE"] = data_row[3]
        cache_row["EMAIL"] = data_row[4]
        cache_row["COUNTRY"] = data_row[5]
        self.record_cache[data_row[4]] = cache_row
    
    def params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.name().surname(), value.name().name(), value.regdate, value.country().code(), value.email)
        return (value.name().surname(), value.name().name(), value.regdate, value.email, value.country().code())