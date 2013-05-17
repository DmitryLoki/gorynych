from txpostgres import txpostgres
from twisted.application import service

from gorynych import BaseOptions
from gorynych.processor.services.trackservice import TrackService
from gorynych.common.infrastructure import persistence
from gorynych.eventstore.eventstore import EventStore
from gorynych.eventstore.store import PGSQLAppendOnlyStore


class Options(BaseOptions):
    pass


def makeService(config, services=None):
    if not services:
        services = service.MultiService()
    pool = txpostgres.ConnectionPool(None,
                                     host=config['dbhost'],
                                     database=config['dbname'],
                                     user=config['dbuser'],
                                     password=config['dbpassword'],
                                     min=config['poolthreads'])

    track_service = TrackService(pool)

    # EventStore init
    event_store = EventStore(PGSQLAppendOnlyStore(pool))
    persistence.add_event_store(event_store)

    track_service.setServiceParent(services)
