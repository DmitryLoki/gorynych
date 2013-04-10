from zope.interface.declarations import implements
from gorynych.info.domain.transport import ITransportRepository, TransportFactory

SQL_SELECT_TRANSPORT = "SELECT TRANSPORT_ID, TRANSPORT_TYPE, TITLE, DESCRIPTION \
FROM TRANSPORT WHERE TRANSPORT_ID = %s"
SQL_INSERT_TRANSPORT = "INSERT INTO TRANSPORT (TRANSPORT_TYPE, TITLE, DESCRIPTION \
VALUES(%s, %s, %s) RETURNING TRANSPORT_ID"
SQL_UPDATE_TRANSPORT = "UPDATE TRANSPORT SET TRANSPORT_TYPE = %s, TITLE = %s, \
DESCRIPTION = %s WHERE TRANSPORT_ID = %s"

class PGSQLTransportRepository(object):
    implements(ITransportRepository)

    def __init__(self, connection = None):
        self.record_cache = dict()
        self.set_connection(connection)
    
    def set_connection(self, connection):
        self.connection = connection

    def get_by_id(self, transport_id):
        result = None
        factory = TransportFactory()
        if transport_id in self.record_cache:
            cache_row = self.record_cache[transport_id]
            result = factory.create_transport(
                cache_row["TRANSPORT_ID"], 
                cache_row["TRANSPORT_TYPE"], 
                cache_row["TITLE"], 
                cache_row["DESCRIPTION"]
                )
        else:
            if self.connection is not None:
                cursor = self.connection.cursor()
                cursor.execute(SQL_SELECT_TRANSPORT, (transport_id,))
                data_row = cursor.fetchone()
                if data_row is not None:
                    result = factory.create_transport(
                        data_row[0],
                        data_row[1],
                        data_row[2],
                        data_row[3]
                    )
                    self.copy_from_data_row(data_row)
        return result

    def save(self, value):
        if self.connection is not None:
            cursor = self.connection.cursor()
            if value.id is None:
                cursor.execute(SQL_INSERT_TRANSPORT, self.params(value))
                data_row = cursor.fetchone()
                if data_row is not None:
                    value.id = data_row[0]
            else:
                cursor.execute(SQL_UPDATE_TRANSPORT, self.params(value, True))
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
        cache_row["TRANSPORT_ID"] = value.id
        cache_row["TRANSPORT_TYPE"] = value.type
        cache_row["TITLE"] = value.title
        cache_row["DESCRIPTION"] = value.description
        self.record_cache[value.id] = cache_row

    def copy_from_data_row(self, data_row):
        cache_row = dict()
        cache_row["TRANSPORT_ID"] = data_row[0]
        cache_row["TRANSPORT_TYPE"] = data_row[1]
        cache_row["TITLE"] = data_row[2]
        cache_row["DESCRIPTION"] = data_row[3]
        self.record_cache[data_row[0]] = cache_row
    
    def params(self, value = None, with_id = False):
        if value is None:
            return ()
        if with_id:
            return (value.type, value.title, value.description, value.id)
        return (value.type, value.title, value.description)
