import os

from txpostgres import txpostgres
from twisted.application import service, internet
from twisted.web import server

from gorynych import BaseOptions
from gorynych.processor.services.visualization import TrackVisualizationService
# TODO: remove this dependency
from gorynych.info.restui import base_resource
from gorynych.info.domain.race import IRaceRepository
from gorynych.info.infrastructure.persistence import PGSQLRaceRepository
from gorynych.common.infrastructure import persistence
from gorynych.eventstore.store import PGSQLAppendOnlyStore
from gorynych.eventstore.eventstore import EventStore


class Options(BaseOptions):
    optParameters = [
        ['webport', 'wp', 8886, None, int]
    ]


def makeService(config, services=None):
    if not services:
        services = service.MultiService()
    pool = txpostgres.ConnectionPool(None,
                                     host=config['dbhost'],
                                     database=config['dbname'],
                                     user=config['dbuser'],
                                     password=config['dbpassword'],
                                     min=config['poolthreads'])
    vis_service = TrackVisualizationService(pool)
    vis_service.setServiceParent(services)

    event_store = EventStore(PGSQLAppendOnlyStore(pool))
    persistence.add_event_store(event_store)

    persistence.register_repository(IRaceRepository,
                                    PGSQLRaceRepository(pool))

    # Web-interface init
    yamlfile = os.path.join(os.path.dirname(__file__), 'vis.yaml')
    web_tree = base_resource.resource_tree(yamlfile)
    site_factory = server.Site(base_resource.APIResource(web_tree, vis_service))

    internet.TCPServer(config['webport'], site_factory,
                   interface='localhost').setServiceParent(services)
    return services
