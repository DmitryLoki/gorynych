'''
Aggregate Race.
'''
__author__ = 'Boris Tsema'
from collections import defaultdict
from copy import deepcopy
import re
import json

import pytz
from zope.interface.interfaces import Interface


from gorynych.common.domain.model import AggregateRoot, ValueObject
from gorynych.common.domain.types import Checkpoint, Country, Name
from gorynych.common.domain.services import times_from_checkpoints
from gorynych.common.domain.events import ArchiveURLReceived, \
    RaceCheckpointsChanged
from gorynych.common.infrastructure import persistence
from gorynych.common.exceptions import TrackArchiveAlreadyExist
from gorynych.info.domain.ids import RaceID, PersonID, TrackerID
from gorynych.common.domain.types import checkpoint_from_geojson

PATTERN = r'https?://airtribune.com/\w+'
#PATTERN = r'https?://localhost:8080/\w+'


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
                    paragliders, checkpoints, transport=None, **kw):
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
        @param transport: list of transport ids
        @type transport: list
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
        result = Race(race_id)
        race_type = ''.join(race_type.strip().lower().split())
        if race_type in RACETASKS.keys():
            result.task = RACETASKS[race_type]()
        else:
            raise ValueError("Unknown race type.")
        if kw.get('timelimits'):
            result.timelimits = kw['timelimits']
        result.title = title
        result.timezone = timezone
        result = self._fill_with_paragliders(result, paragliders)
        if transport:
            result = self._fill_with_transport(result, transport)
        result.checkpoints = checkpoints
        if race_type == 'opendistance':
            result.task.bearing = kw['bearing']
        return result

    def _fill_with_paragliders(self, result, paragliders):
        '''
        @param paragliders: list of Paraglider.
        @type paragliders: C{list}
        '''
        for p in paragliders:
            result.paragliders[p.contest_number] = p
        return result

    def _fill_with_transport(self, result, transport):
        '''

        @param result:
        @type result: gorynych.info.domain.race.Race
        @param transport:[(type, title, desc, tracker_id, transport_id), ...]
        @type transport: list
        @return:
        @rtype:
        '''
        tr_list = []
        if transport and isinstance(transport, list):
            for row in transport:
                tr_list.append({'type':row[0],
                                'title':row[1],
                                'description': row[2],
                                'tracker_id': row[3],
                                'transport_id': row[4]})
        result.transport = tr_list
        return result


class Race(AggregateRoot):
    def __init__(self, race_id):
        super(Race, self).__init__()
        self.id = race_id
        self.task = None
        self._checkpoints = []
        self._title = ''
        self.timelimits = ()
        self.paragliders = dict()
        # [{type, title, description, tracker_id, transport_id}, ]
        self.transport = list()
        self._timezone = pytz.utc
        self.start_time = 0
        self.end_time = 0

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value.strip()

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
            raise TypeError("Bearing can't be set for race type %s" %
                            self.type)
        self.task.bearing = int(value)

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
        if checkpoints == self._checkpoints:
            return
        st, et = times_from_checkpoints(checkpoints)
        if self.timelimits and (
                    st < self.timelimits[0] or et > self.timelimits[1]):
            raise ValueError(
                "Race start time %s or end time %s out of contest start time:end "
                "time interval %s-%s." % (st, et, self.timelimits[0], self.timelimits[1])
            )
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
        self.start_time, self.end_time = st, et
        # Notify other systems about checkpoints changing if previous
        # checkpoints existed.
        if old_checkpoints:
            persistence.event_store().persist(
                                RaceCheckpointsChanged(self.id, checkpoints))

    def _invariants_are_correct(self):
        has_paragliders = len(self.paragliders) > 0
        has_checkpoints = len(self.checkpoints) > 0
        has_task = issubclass(self.task.__class__, RaceTask)
        return has_paragliders and has_checkpoints and has_task

    def _rollback_set_checkpoints(self, old_checkpoints):
        self._checkpoints = old_checkpoints

    @property
    def track_archive(self):
        track_archive = TrackArchive(self.events)
        return track_archive

    def add_track_archive(self, url):
        if not self.track_archive.state == 'no archive':
            raise TrackArchiveAlreadyExist("Track archive with url %s "
                                           "has been added already." % url)
        url_pattern = PATTERN
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

    @property
    def optimum_distance(self):
        from gorynych.processor.domain.services import JavaScriptShortWay
        return JavaScriptShortWay().calculate(self.checkpoints)[1]


class TrackArchive(object):
    states = ['no archive', 'unpacked', 'parsed']
    def __init__(self, events):
        self._state = 'no archive'
        self.progress = defaultdict(set)
        for event in events:
            self.apply(event)

    def apply(self, ev):
        '''
        Apply event from list one by one.
        @param ev: event from list
        @type ev: subclasses of L{DomainEvent}
        @return:
        @rtype:
        '''
        evname = ev.__class__.__name__
        if hasattr(self, 'apply_' + evname):
            getattr(self, 'apply_' + evname)(ev)

    def apply_TrackArchiveUnpacked(self, ev):
        self.state = 'unpacked'
        tracks, extra_tracks, pers_without_tracks = ev.payload
        for item in tracks:
            self.progress['paragliders_found'].add(item['contest_number'])
        for item in extra_tracks:
            self.progress['extra_tracks'].add(item.split('/')[-1])
        for item in pers_without_tracks:
            self.progress['without_tracks'].add(item)

    def apply_RaceGotTrack(self, ev):
        if ev.payload['track_type'] == 'competition_aftertask':
            self.progress['parsed_tracks'].add(ev.payload['contest_number'])

    def apply_TrackArchiveParsed(self, ev):
        self.state = 'parsed'

    def apply_TrackWasNotParsed(self, ev):
        self.progress['unparsed_tracks'].add((ev.payload['contest_number'],
                                       ev.payload['reason']))

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        if self.states.index(self.state) < self.states.index(state):
            self._state = state


class Paraglider(ValueObject):

    def __init__(self, person_id, name, country, glider, contest_number,
                 tracker_id=None):

        if not isinstance(person_id, PersonID):
            person_id = PersonID().fromstring(person_id)
        if not isinstance(name, Name):
            raise TypeError("Name must be an instance of Name class.")
        if not isinstance(country, Country):
            country = Country(country)
        if tracker_id and not isinstance(tracker_id, TrackerID):
            tracker_id = TrackerID.fromstring(tracker_id)

        self.person_id = person_id
        self._name = name
        self.country = country.code()
        self.glider = glider.strip().split(' ')[0].lower()
        self.contest_number = contest_number
        self.tracker_id = tracker_id
        self._contest_track_id = None

    @property
    def name(self):
        return self._name.short()

    @property
    def contest_track_id(self):
        return self._contest_track_id

    @contest_track_id.setter
    def contest_track_id(self, value):
        self._contest_track_id = str(value)

    def __eq__(self, other):
        return self.person_id == other.person_id and (self.glider == other
        .glider) and (self.contest_number == other.contest_number) and (self
                                                                                       .tracker_id == other.tracker_id)


def change_race_transport(rc, params):
    return rc


def change_race(contest_race, race_params):
    '''
    Change information about race in contest.
    @param params:
    @type params:
    @return: Race
    @rtype:
    '''
    if 'checkpoints' in race_params:
        if isinstance(race_params['checkpoints'], (str, unicode)):
            try:
                ch_list = json.loads(
                    race_params['checkpoints'])['features']
            except Exception as e:
                raise ValueError(
                    "Problems with checkpoint reading: %r .Got %s, %r" %
                                (e, type(race_params['checkpoints']),
                                    race_params['checkpoints']))
        elif isinstance(race_params['checkpoints'], dict):
            ch_list = race_params['checkpoints']['features']
        else:
            raise ValueError(
                "Problems with checkpoint reading: got %s, %r" %
                (type(race_params['checkpoints']), race_params['checkpoints']))
        checkpoints = []
        for ch in ch_list:
            checkpoints.append(checkpoint_from_geojson(ch))
        contest_race.checkpoints = checkpoints
    if 'title' in race_params:
        contest_race.title = race_params['title']
    if 'bearing' in race_params:
        contest_race.bearing = race_params['bearing']
    return contest_race


def create_race_for_contest(cont, person_list,
                            transport_list, race_params):
    paragliders = cont.paragliders
    persons = {p.id: p for p in person_list}
    plist = []

    for key in paragliders:
        pers = persons[key]
        plist.append(Paraglider(key, pers.name, pers.country,
                     paragliders[key]['glider'],
                     paragliders[key]['contest_number'],
                     pers.trackers.get(cont.id)))

    factory = RaceFactory()
    r = factory.create_race(race_params['title'], race_params['race_type'],
                            cont.timezone, plist,
                            race_params['checkpoints'],
                            bearing=race_params.get('bearing'),
                            transport=transport_list,
                            timelimits=(cont.start_time, cont.end_time))
    return r
