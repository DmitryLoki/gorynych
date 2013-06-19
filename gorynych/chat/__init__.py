'''
Chat server realization for retrieve.
'''
from twisted.application import internet, service
from twisted.enterprise import adbapi
from twisted.web.resource import IResource
from twisted.web import server
from twisted.python import components

from gorynych import BaseOptions
from gorynych.chat.application import IChatService
from gorynych.chat.restui.resources import WebChat

class Options(BaseOptions):
    optParameters = [
        ['webport', 'wp', 8085, None, int]
    ]

components.registerAdapter(WebChat, IChatService, IResource)

def makeService(config):
    from gorynych.chat.application import ChatApplication, IChatService
    from gorynych.chat.infrastructure import MessageRepository
    from gorynych.chat.domain.services import AuthenticationService
    pool = adbapi.ConnectionPool('psycopg2', database=config['dbname'],
        user=config['dbuser'],
        password=config['dbpassword'],
        host=config['dbhost'])

    s = service.MultiService()
    r = MessageRepository(pool)
    ca = ChatApplication(r, AuthenticationService(pool))
    ca.setServiceParent(s)

    # website
    site = server.Site(IResource(ca))
    j = internet.TCPServer(config['webport'], site)
    j.setServiceParent(s)

    return s
