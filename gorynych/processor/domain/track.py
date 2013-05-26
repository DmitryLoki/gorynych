'''
Track aggregate.
'''
from collections import deque

__author__ = 'Boris Tsema'

from zope.interface import Interface, Attribute, implementer

from gorynych.common.domain.model import AggregateRoot
from gorynych.common.infrastructure import persistence as pe
from gorynych.processor.domain import services
from gorynych.processor import events


class OfflineCorrectorMixin:
    '''
    Cut track and correct it.
    '''
    maxdiff = 1
    def correct_track(self, track):
        pass


class OnlineCorrectorMixin:
    '''
    Here I check that all data has been taken in correct order. Only reorder
     work will be here.
    '''

    def check_data(self, data):
        pass



class ParagliderTrackMixin:
    def sky_earth_definer(self):
        pass


class CompetitionTrack:
    def __init__(self, tracktask):
        self.tracktask = tracktask
        # TODO: implement good buffer for track points.
        self.trackbuffer = deque(50)

    def process_task_data(self, data, trackstate):
        returned_events = []
        a = len(trackstate)
        result, trackstate = self.tracktask.process(data, trackstate)
        for item in trackstate[a-1:]:
            returned_events.append(self.analyze_competition_event(item))
        return trackstate, returned_events

    def analyze_competition_event(self, item):
        pass


class Track(AggregateRoot):

    def __init__(self, id, track_type):
        self.id = id
        self.type = track_type
        # TODO: implement track state with ts as a key, ordered dict mb?
        self.state = dict()

    def apply_TrackDataReceived(self, ev):
        '''
        Process received data and emit event if occur.
        @param ev: TrackDataReceived event
        @type ev: implementor of L{IEvent}
        @return:
        @rtype: C{Deferred}
        '''
        self.state, new_event = self.type.process(ev.payload, self.state)
        if new_event:
            # TODO: implement list handling in EventStore.persist().
            return pe.event_store().persist(new_event)


class ITrackType(Interface):

    def process(data, state):
        '''
        Process data for track, change track state and emit occured event.
        @param data:
        @type data:
        @param state: track's state.
        @type state: C{dict}
        @return: new track state and DomainEvent if occured.
        @rtype: C{tuple} of C{dict} and C{IEvent} or C{None}
        '''


@implementer(ITrackType)
class CompetitionOnline(CompetitionTrack,
                        OnlineCorrectorMixin,
                        ParagliderTrackMixin):

    def process(self, data, trackstate):
        takeoff_time, landing_time = self.sky_earth_definer()
        data = self.check_data(data)
        # Some state work and event publishing.
        return self.process_task_data(data, trackstate)


@implementer(ITrackType)
class CompetitionAftertask(CompetitionTrack,
                           OfflineCorrectorMixin,
                           ParagliderTrackMixin):

    def process(self, trackfile, trackstate):
        parsed_track = services.choose_offline_parser(trackfile)(
                                                self.tracktask.start_time,
                                                self.tracktask.end_time
                                                ).parse(trackfile)
        trackdata = self.correct_track(parsed_track)
        vspeeds = services.vspeed_calculator()
        gspeeds = services.gspeed_calculator()
        takeoff_time, landing_time = self.sky_earth_definer()
        # TODO: persist domain events TrackStarted and TrackEnded.
        # Here I have correct track points from take off to landing.
        return self.process_task_data(trackdata, trackstate)


class TrackTask:
    '''
    Incapsulate race parameters calculation.
    '''

    def __init__(self, checkpoints, start_time, end_time):
        self.chs = checkpoints
        self.start_time = start_time
        self.end_time = end_time

    def process(self, data, trackstate):
        pass