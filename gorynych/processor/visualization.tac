import os

from txpostgres import txpostgres
from twisted.application import service, internet
from twisted.web import server

from gorynych import OPTS
from gorynych.processor.services.visualization import TrackVisualizationService
# TODO: remove this dependency
from gorynych.info.restui import base_resource


# Visualization service init

pool = txpostgres.ConnectionPool(None,
                                 host=OPTS['db']['host'],
                                 database=OPTS['db']['database'],
                                 user=OPTS['db']['user'],
                                 password=OPTS['db']['password'],
                                 min=10)
vis_service = TrackVisualizationService(pool)

# Web-interface init
yamlfile = os.path.join(os.path.dirname(__file__), 'vis.yaml')
web_tree = base_resource.resource_tree(yamlfile)
site_factory = server.Site(base_resource.APIResource(web_tree, vis_service))

# Twisted application staff
application = service.Application('Data for Visualization')

s_collection = service.IServiceCollection(application)

vis_service.setServiceParent(s_collection)
internet.TCPServer(8886, site_factory,
                   interface='localhost').setServiceParent(s_collection)
