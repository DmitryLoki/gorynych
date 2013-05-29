'''
Track aggregate.
'''
from collections import deque

__author__ = 'Boris Tsema'

from zope.interface import Interface, Attribute, implementer
import numpy.ma as ma
import numpy as np

from gorynych.common.domain.model import AggregateRoot
from gorynych.common.infrastructure import persistence as pe
from gorynych.processor.domain import services


class OfflineCorrectorMixin:
    '''
    Cut track and correct it.
    '''
    # Maximum gap in track after which it accounted as finished (in seconds).
    maxtimediff = 300

    def _clean_timestamps(self, track):
        '''
        Cut track in time and make array with timestamps monotonic.
        @param track:
        @type track:
        @return:
        @rtype:
        '''
        data = ma.masked_inside(track, self.tracktask.start_time,
                                self.tracktask.end_time)
        track = track.compress(data.mask)
        # Eliminate repetitive points.
        times, indices = np.unique(track['timestamp'], return_index=True)
        track = track[indices]
        # Here we still can has points reversed in time. Fix it.
        tdifs = np.ediff1d(data['timestamp'], to_begin=1)
        # At first let's find end of track by timeout, if any.
        track_end_idxs = np.where(tdifs > self.maxtimediff)[0]
        if track_end_idxs:
            track_end_idxs = track_end_idxs[0]
            track = track[:track_end_idxs]
            tdifs = tdifs[:track_end_idxs]

        # Eliminate reverse points.
        data = ma.masked_greater(tdifs, 0)
        track = track.compress(data.mask)
        return track

    def correct_track(self, track):
        '''
        Receive raw parsed data, cut it and looks for bad times.
        @param track: array with dtype defined in L{CompetitionTrack}
        @type track: C{numpy.array}
        @return track without dublicated or reversed points in timescale.
        @rtype: C{numpy.array}
        '''
        # Eliminate points outside task time.
        track = self._clean_timestamps(track)
        return services.ParaglidingTrackCorrector().correct_data(track)


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
    # np.array dtype for data
    dtype = [('id', 'i8'), ('timestamp', 'i4'), ('lat', 'f4'),
             ('lon', 'f4'),
             ('alt', 'i2'), ('g_speed', 'f4'), ('v_speed', 'f4'),
             ('distance', 'i4')]

    def __init__(self, tracktask):
        self.tracktask = tracktask
        # TODO: implement good buffer for track points.
        self.trackbuffer = deque(50)
        self.data = np.empty(1, self.dtype)

    def process_task_data(self, data, trackstate):
        returned_events = []
        a = len(trackstate)
        result, trackstate = self.tracktask.process(data, trackstate)
        for item in trackstate[a - 1:]:
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


class ITrackTask(Interface):
    '''
    Incapsulate race parameters calculation.
    Stateless object.
    '''

    def process(data, trackstate):
        '''
        Process data according to concrete track task algorithm.
        @param data: processing data.
        @type data: iterator
        @param trackstate: object implementing Track state.
        @type trackstate: unknown
        @return (trackstate, new events occured during processing)
        @rtype C{tuple}
        '''

    tasktype = Attribute("Name of the task.")
    checkpoints = Attribute("List with Checkpoints.")
    start_time = Attribute("Task start time. unixtime")
    end_time = Attribute("Task end time.unixtime")


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
        try:
            parsed_track = services.choose_offline_parser(trackfile)(
                self.dtype
            ).parse(trackfile)
        except Exception as e:
            raise Exception("Error while parsing file: %r " % e)
        try:
            track = self.correct_track(parsed_track)
        except Exception as e:
            raise Exception("Error while correcting track: %r " % e)
        track['v_speed'] = services.vspeed_calculator(track['alt'],
                                                      track['timestamp'])
        track['g_speed'] = services.gspeed_calculator(track['lat'],
                                                      track['lon'],
                                                      track['timestamp'])
        takeoff_time, landing_time = self.sky_earth_definer()
        # TODO: persist domain events TrackStarted and TrackEnded.
        # Here I have correct track points from take off to landing.
        return self.process_task_data(track, trackstate)


class TrackTask:
    '''
    Incapsulate race parameters calculation.
    '''

    def __init__(self, checkpoints):
        self.chs = checkpoints

    def process(self, data, trackstate):
        pass