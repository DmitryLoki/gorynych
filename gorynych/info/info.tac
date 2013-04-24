'''
Info application for paragliders. Test version with cPickle' repository.
'''
from twisted.application import internet, service
from twisted.web import server

from gorynych import OPTS
from gorynych.info.application import ApplicationService
from gorynych.common.infrastructure.messaging import DomainEventsPublisher
from gorynych.info.restui import base_resource
from gorynych.info.domain.contest import IContestRepository
from gorynych.info.domain.race import IRaceRepository
from gorynych.info.domain.person import IPersonRepository
from gorynych.common.infrastructure import persistence
from gorynych.info.test.helpers import PickleContestRepository, PicklePersonRepository, PickleRaceRepository


api_tree = base_resource.resource_tree()
persistence.register_repository(IContestRepository, PickleContestRepository
    ('contest_repo'))
persistence.register_repository(IRaceRepository, PickleRaceRepository
    ('race_repo'))
persistence.register_repository(IPersonRepository, PicklePersonRepository
    ('person_repo'))

application = service.Application('Gorynych Info System')


app_service = ApplicationService(DomainEventsPublisher())
s_collection = service.IServiceCollection(application)

app_service.setServiceParent(s_collection)
site_factory = server.Site(base_resource.APIResource(api_tree, app_service))
internet.TCPServer(OPTS['info']['web_port'], site_factory,
   interface='localhost').setServiceParent(s_collection)