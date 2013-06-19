__author__ = 'Boris Tsema'
from twisted.application.service import ServiceMaker

info = ServiceMaker('chat', 'gorynych.chat', 'Retrieve chat for Gorynych.',
    'gchat')
