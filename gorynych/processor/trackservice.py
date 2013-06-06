from twisted.application import service
from twisted.enterprise import adbapi

from gorynych import BaseOptions
from gorynych.processor.services.trackservice import TrackService, ProcessorService
from gorynych.processor.infrastructure.persistence import TrackRepository
from gorynych.common.infrastructure import persistence
from gorynych.eventstore.eventstore import EventStore
from gorynych.eventstore.store import PGSQLAppendOnlyStore


class Options(BaseOptions):
    pass


def makeService(config, services=None):
    if not services:
        services = service.MultiService()

    pool = adbapi.ConnectionPool('psycopg2', database=config['dbname'],
        user=config['dbuser'],
        password=config['dbpassword'],
        host=config['dbhost'])

    # EventStore init
    event_store = EventStore(PGSQLAppendOnlyStore(pool))
    persistence.add_event_store(event_store)

    track_repository = TrackRepository(pool)

    track_service = TrackService(pool, event_store, track_repository)
    processor_service = ProcessorService(pool, event_store)

    track_service.setServiceParent(services)
    processor_service.setServiceParent(services)

    return services
