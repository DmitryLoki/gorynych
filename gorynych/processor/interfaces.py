__author__ = 'Boris Tsema'

from zope.interface import Interface, Attribute

class ITrackType(Interface):
    '''
    I am a track type. I define all operations which are depend of track
    type, i.e. competition, online, offline.
    '''
    type = Attribute("String which is a name of track type.")

    def read(data):
        '''
        I read or parse passed data and return it in common format.
        @param data: data passed to me.
        @type data:
        @return: array with dtype L{gorynych.processor.domain.track.DTYPE}
        @rtype: C{numpy.ndarray}
        '''

    def process(data, start_time, end_time, trackstate):
        '''
        I read passed data and calculate something is necessary.
        @param data: passed data
        @type data:
        @param start_time:
        @type start_time:
        @param end_time:
        @type end_time:
        @param trackstate: state of track which I process.
        @type trackstate: L{gorynych.processor.domain.track.TrackState}
        @return: array with dtype L{gorynych.processor.domain.track.DTYPE}
        and list with occured events.
        @rtype: C{numpy.ndarray}, C{list}
        '''

    def correct(obj):
        '''
        I do postprocessing work - correct points or create track events.
        @param obj: track which I process.
        @type obj: C{gorynych.processor.domain.track.Track}
        @return: list of occured events.
        @rtype: C{list}
        '''
