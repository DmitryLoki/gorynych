'''
Realization of persistence logic.
'''
import psycopg2

from zope.interface.declarations import implements

from gorynych.info.domain.person import IPersonRepository


class PersonRepository(object):
    '''
    Implement collection-like interface of Person aggregate instances.
    '''
    implements(IPersonRepository)
    pass

connectionParams = {
    "server":"localhost",
    "dbname":"airtribune",
    "user":"airtribune",
    "password":"airtribune",
    "schema":"airtribune_test"
}

class ConnectionManager(object):
    def open_connection(self):
        global connectionParams
        server_name = connectionParams["server"]
        db_name = connectionParams["dbname"]
        user_name = connectionParams["user"]
        user_pass = connectionParams["password"]
        schema_name = connectionParams["schema"]

        connection = psycopg2.connect(
            host = server_name, 
            database = db_name, 
            user = user_name, 
            password = user_pass)
        connection.cursor().execute("SET search_path TO %s", (schema_name,))
        connection.commit()
        return connection
