'''
Package for context which collect information and supply other context with
it.
'''
from txpostgres import txpostgres
from twisted.application import internet, service
from twisted.web import server

from gorynych import BaseOptions
from gorynych.info.application import ApplicationService
from gorynych.info.restui import base_resource
# import persistence staff
from gorynych.info.domain.contest import IContestRepository
from gorynych.info.domain.race import IRaceRepository
from gorynych.info.domain.person import IPersonRepository
from gorynych.common.infrastructure import persistence
from gorynych.eventstore.eventstore import EventStore
from gorynych.eventstore.store import PGSQLAppendOnlyStore
from gorynych.info.infrastructure.persistence import PGSQLContestRepository,\
    PGSQLPersonRepository, PGSQLRaceRepository

class Options(BaseOptions):
    optParameters = [
        ['webport', 'wp', 8086, None, int]
    ]

def makeService(config, services=None):
    '''
    Create services
    @param config:
    @type config:
    @param services: service.IServiceCollection implementation.
    @type services:
    @return:
    @rtype:
    '''
    if not services:
        services = service.MultiService()
    pool = txpostgres.ConnectionPool(None,
                                     host=config['dbhost'],
                                     database=config['dbname'],
                                     user=config['dbuser'],
                                     password=config['dbpassword'],
                                     min=config['poolthreads'])

    # EventStore init
    event_store = EventStore(PGSQLAppendOnlyStore(pool))
    persistence.add_event_store(event_store)

    # Application Service init
    app_service = ApplicationService(event_store)
    app_service.setServiceParent(services)

    # Test repositories init
    persistence.register_repository(IContestRepository,
                                    PGSQLContestRepository(pool) )
    persistence.register_repository(IRaceRepository,
                                    PGSQLRaceRepository(pool))
    persistence.register_repository(IPersonRepository,
                                    PGSQLPersonRepository(pool))

    # REST API init
    api_tree = base_resource.resource_tree()
    site_factory = server.Site(base_resource.APIResource(api_tree, app_service))

    internet.TCPServer(config['webport'], site_factory,
                       interface='localhost').setServiceParent(services)
    return services
