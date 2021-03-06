'''
Package for context which collect information and supply other context with
it.
'''
from twisted.application import internet, service
from twisted.web import server
from twisted.enterprise import adbapi

from gorynych import BaseOptions

class Options(BaseOptions):
    optParameters = [
        ['webport', 'wp', 8085, None, int]
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
    from gorynych.info.application import ApplicationService, LastPointApplication
    from gorynych.info.restui import base_resource
    # import persistence staff
    from gorynych.info.domain import interfaces
    from gorynych.common.infrastructure import persistence
    from gorynych.common.infrastructure.messaging import RabbitMQObject
    from gorynych.eventstore.eventstore import EventStore
    from gorynych.eventstore.store import PGSQLAppendOnlyStore
    from gorynych.info.infrastructure.persistence import PGSQLContestRepository, PGSQLPersonRepository, PGSQLRaceRepository, PGSQLTrackerRepository, PGSQLTransportRepository
    # Time sinchronization. TODO: find better place for it.
    from gorynych.info.restui.resources import TimeResource

    if not services:
        services = service.MultiService()

    pool = adbapi.ConnectionPool('psycopg2', database=config['dbname'],
                                 user=config['dbuser'],
                                 password=config['dbpassword'],
                                 host=config['dbhost'], cp_max=10,
                                 cp_reconnect=True)

    # EventStore init.
    event_store = EventStore(PGSQLAppendOnlyStore(pool))
    persistence.add_event_store(event_store)

    # Application Service init.
    app_service = ApplicationService(pool, event_store)
    app_service.setServiceParent(services)

    # LastPoint application service init.
    rabbit_connection = RabbitMQObject(host='localhost', port=5672,
                                       exchange='receiver', queues_no_ack=True,
                                       exchange_type='fanout')
    last_point = LastPointApplication(pool, rabbit_connection)
    last_point.setServiceParent(services)

    # Repositories init.
    persistence.register_repository(interfaces.IContestRepository,
                                    PGSQLContestRepository(pool) )
    persistence.register_repository(interfaces.IRaceRepository,
                                    PGSQLRaceRepository(pool))
    persistence.register_repository(interfaces.IPersonRepository,
                                    PGSQLPersonRepository(pool))
    persistence.register_repository(interfaces.ITrackerRepository,
        PGSQLTrackerRepository(pool))
    persistence.register_repository(interfaces.ITransportRepository,
        PGSQLTransportRepository(pool))

    # REST API init
    api_tree = base_resource.resource_tree()
    api_resource = base_resource.APIResource(api_tree, app_service)
    api_resource.putChild('time', TimeResource())
    site_factory = server.Site(api_resource)

    internet.TCPServer(config['webport'], site_factory,
                       interface='localhost').setServiceParent(services)
    return services
