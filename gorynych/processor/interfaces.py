'''
Interfaces for context processor.
'''
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

    def postprocess(obj):
        '''
        I do postprocessing work - correct points or create track events.
        @param obj: track which I process.
        @type obj: C{gorynych.processor.domain.track.Track}
        @return: list of occured events.
        @rtype: C{list}
        '''


class IRaceType(Interface):
    '''
    I am a type of race task like Open Distance or Race to Goal.
    '''

    type = Attribute("A C{str} with name race name in lowercase and without "
                     "any delimiters.")

    start_time = Attribute("An C{int} with unixtime of moment from which "
                           "a race activity became an object of our interest.")
    end_time = Attribute("An C{int} with unixtime of moment then race "
                         "stopped.")

    def process(points, trackstate, aggregate_id):
        '''
        I process taken points and calculate what is necessary.
        @param points: points for processing. Usually array of points for
        some interval. It can be a whole track or just a part of it (in
        livetrack mode).
        @type points: C{numpy.ndarray} with dtype=L{gorynych.processor.domain.track.DTYPE}.
        @param trackstate: read-only object which implement track state.
        @type trackstate: L{gorynych.processor.domain.track.TrackState}.
        @param aggregate_id: id of Track aggregate for which calculations
        are performed.
        @type aggregate_id: subclass of DomainIdentifier.
        @return: tuple of length two. Tuple consist of processed
        points array with full information about those points and list of
        DomainEvents which occur while processing.
        @rtype: (numpy.ndarray, list)
        '''