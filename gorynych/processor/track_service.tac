from txpostgres import txpostgres
from twisted.application import service

from gorynych import OPTS
from gorynych.processor.services.trackservice import TrackService
from gorynych.common.infrastructure import persistence
from gorynych.eventstore.eventstore import EventStore
from gorynych.eventstore.store import PGSQLAppendOnlyStore



pool = txpostgres.ConnectionPool(None,
                                 host=OPTS['db']['host'],
                                 database=OPTS['db']['database'],
                                 user=OPTS['db']['user'],
                                 password=OPTS['db']['password'],
                                 min=10)

track_service = TrackService(pool)

# EventStore init
event_store = EventStore(PGSQLAppendOnlyStore(pool))
persistence.add_event_store(event_store)


# Twisted application staff
application = service.Application('Gorynych Info System')

s_collection = service.IServiceCollection(application)

track_service.setServiceParent(s_collection)
