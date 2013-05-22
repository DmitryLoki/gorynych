__author__ = 'Boris Tsema'
from twisted.application.service import ServiceMaker

visualization = ServiceMaker('visualization',
                    'gorynych.processor.visualization',
                    'Tracks visualization.', 'gorynychvisualization')
