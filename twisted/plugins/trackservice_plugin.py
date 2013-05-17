__author__ = 'Boris Tsema'
from twisted.application.service import ServiceMaker

trackservice = ServiceMaker('trackservice',
                    'gorynych.processor.trackservice',
                    'Tracks parser.', 'gorynychtrackservice')
