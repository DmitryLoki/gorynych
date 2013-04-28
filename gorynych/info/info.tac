'''
Info application for paragliders. Test version with cPickle' repository.
'''
from txpostgres import txpostgres
from twisted.application import internet, service
from twisted.web import server

from gorynych import OPTS
from gorynych.info.application import ApplicationService
from gorynych.common.infrastructure.messaging import DomainEventsPublisher
from gorynych.info.restui import base_resource
# import persistence staff
from gorynych.info.domain.contest import IContestRepository
from gorynych.info.domain.race import IRaceRepository
from gorynych.info.domain.person import IPersonRepository
from gorynych.common.infrastructure import persistence
from gorynych.eventstore.eventstore import EventStore
from gorynych.eventstore.store import PGSQLAppendOnlyStore
# imports for test only
from gorynych.info.test.helpers import PickleContestRepository, PicklePersonRepository, PickleRaceRepository

pool = txpostgres.ConnectionPool(None, host=OPTS['db']['host'],
                      database=OPTS['db']['database'], user=OPTS['db']['user'],
                      password=OPTS['db']['password'], min=5)

# EventStore init
event_store = EventStore(PGSQLAppendOnlyStore(pool))
persistence.add_event_store(event_store)

# Test repositories init
persistence.register_repository(IContestRepository, PickleContestRepository
    ('contest_repo'))
persistence.register_repository(IRaceRepository, PickleRaceRepository
    ('race_repo'))
persistence.register_repository(IPersonRepository, PicklePersonRepository
    ('person_repo'))

# Application Service init
app_service = ApplicationService(DomainEventsPublisher(), event_store)

# REST API init
api_tree = base_resource.resource_tree()
site_factory = server.Site(base_resource.APIResource(api_tree, app_service))

# Twisted application staff
application = service.Application('Gorynych Info System')

s_collection = service.IServiceCollection(application)

app_service.setServiceParent(s_collection)

internet.TCPServer(OPTS['info']['web_port'], site_factory,
   interface='localhost').setServiceParent(s_collection)