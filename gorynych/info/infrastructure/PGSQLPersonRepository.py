from zope.interface.declarations import implements
from gorynych.info.domain.person import PersonFactory, IPersonRepository
from gorynych.common.exceptions import NoAggregate

SQL_SELECT_PERSON = "SELECT \
LASTNAME \
, FIRSTNAME \
, COUNTRY \
, EMAIL \
, REGDATE \
, PERSON_ID \
, ID \
FROM PERSON WHERE ID = %s\
"
SQL_INSERT_PERSON = "INSERT INTO PERSON(\
LASTNAME \
, FIRSTNAME \
, EMAIL \
, REGDATE \
, PERSON_ID \
)VALUES(%s, %s, %s, %s, %s) \
RETURNING ID"

SQL_UPDATE_PERSON = "UPDATE PERSON SET \
LASTNAME = %s\
, FIRSTNAME = %s\
, EMAIL = %s\
, REGDATE = %s\
, PERSON_ID = %s \
WHERE ID = %s\
"


class PGSQLPersonRepository(object):
    implements(IPersonRepository)

    def __init__(self, pool):
        self.pool = pool

    def _process_select_result(self, data):
        if len(data) == 1:
            data_row = data[0]
            if data_row is not None:
                regdate = data_row[4]
                factory = PersonFactory()
                result = factory.create_person(
                    data_row[0],
                    data_row[1],
                    data_row[2],
                    data_row[3],
                    regdate.year,
                    regdate.month,
                    regdate.day,
                    data_row[5])
                result._id = data_row[6]
                return result
        raise NoAggregate("Person")

    def _process_insert_result(self, data, value):
        if data is not None and value is not None:
            inserted_id = data[0][0]
            value._id = inserted_id
            return value
        return None

    def _params(self, value=None, with_id=False):
        if value is None:
            return ()
        if with_id:
            return (value.name().surname(), value.name().name(), value.regdate,
                    value.country().code(), value.email)
        return (value.name().surname(), value.name().name(), value.regdate,
                value.email, value.country().code())

    def get_by_id(self, person_id):
        d = self.pool.runQuery(SQL_SELECT_PERSON, (person_id,))
        d.addBoth(self._process_select_result)
        return d

    def save(self, value):
        d = None
        if value._id is not None:
            d = self.pool.runOperation(SQL_UPDATE_PERSON,
                                       self._params(value, True))
            d.addCallback(lambda _: value)
        else:
            d = self.pool.runQuery(SQL_INSERT_PERSON, self._params(value))
            d.addCallback(self._process_insert_result, value)
        return d
