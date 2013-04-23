'''
Realization of persistence logic.
'''
from txpostgres import txpostgres

from zope.interface.declarations import implements

from gorynych.info.domain.person import IPersonRepository


class PersonRepository(object):
    '''
    Implement collection-like interface of Person aggregate instances.
    '''
    implements(IPersonRepository)
    pass

connection_params = {
    "server": "localhost",
    "dbname": "airtribune",
    "user": "airtribune",
    "password": "airtribune"
}


class ConnectionManager(object):
    def __init__(self):
        pass

    def pool(self):
        global connectionParams
        self.pool = txpostgres.ConnectionPool(
            None,
            host=connection_params["server"],
            database=connection_params["dbname"],
            user=connection_params["user"],
            password=connection_params["password"],
            min=8
        )
        d = self.pool.start()
        return d
