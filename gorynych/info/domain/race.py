'''
Aggregate Race.
'''
__author__ = 'Boris Tsema'
from copy import deepcopy
import decimal
import re

import pytz
from zope.interface.interfaces import Interface


from gorynych.common.domain.model import AggregateRoot, ValueObject,\
                                        DomainEvent
from gorynych.common.domain.types import Checkpoint
from gorynych.common.exceptions import BadCheckpoint
from gorynych.info.domain.events import RaceCheckpointsChanged,\
                                        ArchiveURLReceived
from gorynych.common.infrastructure import persistence
from gorynych.info.domain.ids import RaceID


class RaceTask(ValueObject):
    type = None

    def checkpoints_are_good(self, checkpoints):
        if not checkpoints:
            raise ValueError("Race can't be created without checkpoints.")
        for checkpoint in checkpoints:
            if not isinstance(checkpoint, Checkpoint):
                raise TypeError("Wrong checkpoint type.")
        return True


class SpeedRunTask(RaceTask):
    type = 'speedrun'


class RaceToGoalTask(RaceTask):
    type = 'racetogoal'


class OpenDistanceTask(RaceTask):
    type = 'opendistance'
    bearing = None


RACETASKS = {'speedrun': SpeedRunTask,
             'racetogoal': RaceToGoalTask,
             'opendistance': OpenDistanceTask}


class RaceFactory(object):

    def create_race(self, title, race_type, timezone,
                    paragliders, checkpoints, **kw):
        '''

        @param title:
        @type title:
        @param race_type:
        @type race_type:
        @param timelimits:
        @type timelimits:
        @param timezone:
        @type timezone:
        @param paragliders: list of L{Paragliders}
        @type paragliders: C{list}
        @param checkpoints:
        @type checkpoints:
        @param race_id:
        @type race_id:
        @return:
        @rtype:
        '''
        if not kw.has_key('race_id'):
            race_id = RaceID()
        elif isinstance(kw['race_id'], str):
            race_id = RaceID.fromstring(kw['race_id'])
        race = Race(race_id)
        race_type = ''.join(race_type.strip().lower().split())
        if race_type in RACETASKS.keys():
            race.task = RACETASKS[race_type]()
        else:
            raise ValueError("Unknown race type.")
        race.title = title
        race.timezone = timezone
        race = self._fill_with_paragliders(race, paragliders)
        race.checkpoints = checkpoints
        if race_type == 'opendistance':
            race.task.bearing = kw['bearing']

        return race

    def _fill_with_paragliders(self, race, paragliders):
        '''
        @param paragliders: list of Paraglider.
        @type paragliders: C{list}
        '''
        for p in paragliders:
            race.paragliders[p.contest_number] = p
        return race


class CheckpointsAreAddedToRace(DomainEvent):
    '''
    Raised when someone try to add track archive after it has been parsed.
    '''
    def __init__(self, event_id, checkpoints):
        self.checkpoints = checkpoints
        DomainEvent.__init__(self, event_id)


class TrackArchiveAlreadyExist(Exception):
    '''
    Raised when someone try to add track archive after it has been parsed.
    '''


class Race(AggregateRoot):
    def __init__(self, race_id):
        self.id = race_id

        self.task = None
        self._checkpoints = []
        self._title = ''
        self.timelimits = ()
        # {contest_number: Paraglider}
        self.paragliders = dict()
        self._start_time = decimal.Decimal('infinity')
        self._end_time = 1
        self._timezone = pytz.utc

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value.strip().title()

    @property
    def type(self):
        return self.task.type

    @property
    def bearing(self):
        result = None
        try:
            result = self.task.bearing
        except AttributeError:
            pass
        return result

    @bearing.setter
    def bearing(self, value):
        if not self.type == 'opendistance':
            raise TypeError("Bearing can't be set for race type %s" % race
            .type)
        self.task.bearing = int(value)

    @property
    def start_time(self):
        '''
        Time on which race begun.
        @return: Epoch time in seconds.
        @rtype: C{int}
        '''
        return self._start_time

    @property
    def end_time(self):
        '''
        Time when race is ended
        @return: Epoch time in seconds.
        @rtype: C{int}
        '''
        return self._end_time

    @property
    def timezone(self):
        '''
        Race timezone
        @return: string like 'Europe/Moscow'
        @rtype: str
        '''
        return self._timezone

    @timezone.setter
    def timezone(self, value):
        '''
        Set race timezone.
        @param value: string with time zone like 'Europe/Moscow'
        @type value: str
        '''
        if value in pytz.common_timezones_set:
            self._timezone = value

    @property
    def checkpoints(self):
        return self._checkpoints

    @checkpoints.setter
    def checkpoints(self, checkpoints):
        '''
        Replace race checkpoints with a new list. Publish L{
        RaceCheckpointsChanged} event with race id and checkpoints list.
        @param checkpoints: list of L{Checlpoint} instances.
        @type checkpoints: C{list}
        '''
        old_checkpoints = deepcopy(self._checkpoints)
        self._checkpoints = checkpoints
        if not self._invariants_are_correct():
            self._rollback_set_checkpoints(old_checkpoints)
            raise ValueError("Race invariants are violated.")
        try:
            self.task.checkpoints_are_good(checkpoints)
        except (TypeError, ValueError) as e:
            self._rollback_set_checkpoints(old_checkpoints)
            raise e
        self._get_times_from_checkpoints(self._checkpoints)
        # Notify other systems about checkpoints changing if previous
        # checkpoints existed.
        if old_checkpoints:
            print "*"*40
            print "publish event"
            print old_checkpoints
            print self.id, type(self.id)
            persistence.event_store().persist(RaceCheckpointsChanged(self.id,
                                                                checkpoints))

    def _invariants_are_correct(self):
        has_paragliders = len(self.paragliders) > 0
        has_checkpoints = len(self.checkpoints) > 0
        has_task = issubclass(self.task.__class__, RaceTask)
        return has_paragliders and has_checkpoints and has_task

    def _rollback_set_checkpoints(self, old_checkpoints):
        self._checkpoints = old_checkpoints

    def _get_times_from_checkpoints(self, checkpoints):
        start_time = self._start_time
        end_time = self._end_time
        for point in checkpoints:
            if point.open_time and point.open_time < start_time:
                start_time = point.open_time
            if point.close_time and point.close_time > end_time:
                end_time = point.close_time
        if start_time < end_time:
            self._start_time = start_time
            self._end_time = end_time
        else:
            raise BadCheckpoint("Wrong or absent times in checkpoints.")

    @property
    def track_archive(self):
        events = persistence.event_store().load_events(str(self.id))
        # and now events is Deferred instance :(
        # TODO: pass list to TrackArchive, not deferred.
        track_archive = TrackArchive(events)
        return track_archive

    def add_track_archive(self, url):
        if not self.track_archive.state == 'new':
            raise TrackArchiveAlreadyExist("Track archive with url %s "
                                           "already parsed.")
        url_pattern = r'https?://airtribune.com/\w+'
        if re.match(url_pattern, url):
            persistence.event_store().persist(ArchiveURLReceived(self.id,
                                                                 url))
            return "Archive with url %s added." % url
        else:
            raise ValueError("Received URL doesn't match allowed pattern.")

    @property
    def contest_tracks(self):
        result = []
        for p in self.paragliders:
            if p.contest_track_id:
                result.append(p)
        return result


class TrackArchive(object):
    def __init__(self, events):
        self.state = 'new'
        self.progress = 'nothing has been done'
        # for event in events:
        #     self.apply(event)

    def apply(self, event):
        '''
        Apply event from list one by one.
        @param event: event from list
        @type event: subclasses of L{DomainEvent}
        @return:
        @rtype:
        '''
        try:
            getattr(self, '_'.join(('when', event.__class__.__name__.lower(
                ))))(event)
        except AttributeError:
            pass

    def when_archiveurlreceived(self, event):
        self.state = 'work is started'


class IRaceRepository(Interface):
    def get_by_id(id):
        '''

        @param id:
        @type id:
        @return:
        @rtype:
        '''

    def save(obj):
        '''

        @param obj:
        @type obj:
        @return:
        @rtype:
        '''


