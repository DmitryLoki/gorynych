'''
Contest Aggregate.
'''
from copy import deepcopy
import datetime

import pytz

from gorynych.info.domain import transport
from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.common.domain.types import Address, Country, Phone, Checkpoint
from gorynych.common.domain.events import ParagliderRegisteredOnContest
from gorynych.common.infrastructure import persistence
from gorynych.info.domain.ids import ContestID, RaceID
from gorynych.common.exceptions import DomainError
from gorynych.common.domain.services import times_from_checkpoints


class ContestFactory(object):

    def create_contest(self, title, start_time, end_time,
                       contest_place, contest_country, hq_coords, timezone,
                       contest_id=None):
        address = Address(contest_place, contest_country, hq_coords)
        if end_time < start_time:
            raise ValueError("Start time must be less then end time.")
        if not contest_id:
            contest_id = ContestID()
        elif not isinstance(contest_id, ContestID):
            contest_id = ContestID.fromstring(contest_id)
        if not timezone in pytz.all_timezones_set:
            raise pytz.exceptions.UnknownTimeZoneError("Wrong timezone.")
        contest = Contest(contest_id, start_time, end_time, address)
        contest.title = title
        contest.timezone = timezone
        return contest


class Contest(AggregateRoot):

    def __init__(self, contest_id, start_time, end_time, address):
        super(Contest, self).__init__()
        self.id = contest_id
        self._title = ''
        self._timezone = ''
        self._start_time = start_time
        self._end_time = end_time
        self.address = address
        self._participants = dict()
        self.retrieve_id = None
        self._tasks = dict()

    @property
    def timezone(self):
        '''
        @return: full name of time zone in which contest take place (
        Europe/Moscow).
        @rtype: C{str}
        '''
        return self._timezone

    @timezone.setter
    def timezone(self, value):
        '''
        This is a blocking function! It read a file in usual blocking mode
        and it's better to wrap result in maybeDeferred.

        @param value: time zone full name
        @type value: C{str}
        '''
        if value in pytz.all_timezones_set:
            self._timezone = value

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, value):
        if int(value) == self.start_time:
            return
        old_start_time = self.start_time
        self._start_time = int(value)
        if not self._invariants_are_correct():
            self._start_time = old_start_time
            raise ValueError("Incorrect start_time violate aggregate's "
                             "invariants.")

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        if int(value) == self.end_time:
            return
        old_end_time = self.end_time
        self._end_time = int(value)
        if not self._invariants_are_correct():
            self._end_time = old_end_time
            raise DomainError("Incorrect end_time violate aggregate's "
                             "invariants.")

    @property
    def tasks(self):
        return self._tasks.values()

    def _tasks_are_correct(self):
        """
        1) Unique titles.
        2) Each task must fit contest time bounds.
        3) No time overlapping between tasks.
        4) Each task is by itself correct.
        """
        tasks = self._tasks.values()
        titles = [t.title for t in tasks]
        if len(titles) != len(set(titles)):
            return False

        for task in tasks:
            if not task.is_task_correct():
                return False
            if task.start_time < self.start_time or \
                    task.deadline > self.end_time:
                return False

        for i, task in enumerate(tasks):
            for j, other_task in enumerate(tasks[i + 1:]):
                if other_task.start_time >= task.start_time \
                    and other_task.start_time <= task.deadline \
                    or other_task.deadline >= task.start_time \
                        and other_task.deadline <= task.deadline:
                    return False
        return True

    def add_task(self, task):
        if not isinstance(task, BaseTask):
            raise TypeError('Expected BaseTask instance, got {} instead'.format(
                type(task)))
        tasks_before = deepcopy(self._tasks)
        self._tasks[task.id] = task
        if not self._tasks_are_correct():
            self._tasks = tasks_before
            # that's too vague, could we get concrete error message?
            raise ValueError('Contest tasks conditions are violated')

    def get_task(self, task_id):
        return self._tasks[task_id]

    def edit_task(self, task_id, **kwargs):
        tasks_before = deepcopy(self._tasks)
        if task_id in self._tasks:
            for key, value in kwargs.iteritems():
                if hasattr(self._tasks[task_id], key):
                    setattr(self._tasks[task_id], key, value)
        if not self._tasks_are_correct():
            self._tasks = tasks_before
            raise ValueError('Contest tasks conditions are violated')

    def change_times(self, start_time, end_time):
        '''
        Change both start time and end time of context.
        @param start_time:
        @type start_time: C{int}
        @param end_time:
        @type end_time: C{int}
        @return:
        @rtype:
        @raise: ValueError if times violate aggregate's invariants.
        '''
        start_time = int(start_time)
        end_time = int(end_time)
        if int(start_time) >= int(end_time):
            raise ValueError("Start_time must be less then end_time.")
        if start_time == self.start_time:
            self.end_time = end_time
        elif end_time == self.end_time:
            self.start_time = start_time
        else:
            old_start_time = self.start_time
            old_end_time = self.end_time
            self._start_time = start_time
            self._end_time = end_time
            if not self._invariants_are_correct():
                self._start_time = old_start_time
                self._end_time = old_end_time
                raise ValueError("Times values violate aggregate's "
                                 "invariants.")

    @property
    def country(self):
        return self.address.country

    @country.setter
    def country(self, value):
        self.address = Address(self.place, Country(value),
                               self.address.coordinates)

    @property
    def place(self):
        return self.address.place

    @place.setter
    def place(self, value):
        self.address = Address(value, self.address.country,
                               self.address.coordinates)

    @property
    def hq_coords(self):
        '''

        @return:(float, float)
        @rtype: C{tuple}
        '''
        return self.address.coordinates

    @hq_coords.setter
    def hq_coords(self, value):
        self.address = Address(self.place, self.country, value)

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value.strip()

    def register_paraglider(self, pers, glider, cnum):
        '''
        Register person as a paraglider.
        @param pers: person registered
        @type pers: L{gorynych.info.domain.person.Person}
        @param glider: glider manufacturer name
        @type glider: C{str}
        @param cnum: contest number
        @type cnum: C{str}
        @return: self
        '''
        paragliders_before = deepcopy(self._participants)
        glider = glider.strip().split(' ')[0].lower()
        self._participants[pers.id] = dict(
            role='paraglider',
            name=pers.name.full(),
            country=pers.country,
            glider=glider,
            contest_number=int(cnum),
            phone=pers.phone)
        if not self._invariants_are_correct():
            self._participants = paragliders_before
            raise DomainError("Paraglider must have unique contest number.")
        persistence.event_store().persist(ParagliderRegisteredOnContest(
            pers.id, self.id))
        return self

    def add_winddummy(self, pers):
        self._participants[pers.id] = dict(
            role='winddummy',
            name=pers.name.full(),
            phone=pers.phone)
        return self

    def add_organizer(self, pers, description=""):
        self._participants[pers.id] = dict(
            role='organizer',
            name=pers.name.full(),
            email=pers.email,
            description=description)
        return self

    def add_staff_member(self, staffmember):
        self._participants[staffmember.id] = dict(
            role='staff',
            title=staffmember.title,
            type=staffmember.type,
            phone=staffmember.phone,
            description=staffmember.description)
        return self

    def _invariants_are_correct(self):
        """
        Check next invariants for contest:
        every paraglider has unique contest_number
        context start_time is less then end_time
        """
        contest_numbers = set()
        paragliders = set()
        for key in self.paragliders.keys():
                contest_numbers.add(
                    self.paragliders[key]['contest_number'])
                paragliders.add(key)
        all_contest_numbers_uniq = len(paragliders) == len(contest_numbers)

        end_after_start = int(self.start_time) < int(self.end_time)
        return all_contest_numbers_uniq and end_after_start

    def _rollback_register_paraglider(self, paraglider_before, person_id):
        # TODO: this function should rollback all paragliders. Am I need this
        # function?
        self._participants[person_id] = paraglider_before

    def change_participant_data(self, person_id, **kwargs):
        if not kwargs:
            raise ValueError("No new data has been received.")
        try:
            old_participant = deepcopy(self._participants[person_id])
        except KeyError:
            raise ValueError("No participant with such id.")

        for key in kwargs.keys():
            if key == 'contest_number':
                # TODO: check necessity of this.
                kwargs[key] = int(kwargs[key])
            if key == 'glider':
                kwargs[key] = kwargs[key].strip().split(' ')[0].lower()
            self._participants[person_id][key] = kwargs[key]

        if not self._invariants_are_correct():
            self._participants[person_id] = old_participant
            raise ValueError("Contest invariants violated.")

    def _get_participants(self, role):
        result = dict()
        for key in self._participants:
            if self._participants[key]['role'] == role:
                result[key] = self._participants[key]
        return result

    @property
    def paragliders(self):
        return self._get_participants('paraglider')

    @property
    def winddummies(self):
        return self._get_participants('winddummy')

    @property
    def organizers(self):
        return self._get_participants('organizer')

    @property
    def staff(self):
        return self._get_participants('staff')


def change(cont, params):
    '''
    Do changes in contest.
    @param cont:
    @type cont: Contest
    @param params:
    @type params: dict
    @return:
    @rtype: Contest
    '''
    if params.get('start_time') and params.get('end_time'):
        cont.change_times(params['start_time'], params['end_time'])
        del params['start_time']
        del params['end_time']

    if params.get('coords'):
        lat, lon = params['coords'].split(',')
        cont.hq_coords = (lat, lon)
        del params['coords']

    for param in params.keys():
        setattr(cont, param, params[param])
    return cont


def change_participant(cont, participant_data):
    if 'glider' in participant_data:
        cont.change_participant_data(participant_data['person_id'],
                                     glider=participant_data['glider'])
    if 'contest_number' in participant_data:
        cont.change_participant_data(participant_data['person_id'],
                                     contest_number=participant_data['contest_number'])
    return cont


class StaffMember(ValueObject):
    types = frozenset(['rescuer', 'ambulance']).union(transport.TYPES)

    def __init__(self, title, type, description="", phone=None):
        if type not in self.types:
            raise TypeError('Incorrect type ({}). Avaliable types: {}'.format(
                              type, self.types))
        self.title = title
        self.type = type
        if phone:
            self.phone = Phone(phone).number
        else:
            self.phone = ""
        self.id = DomainIdentifier()
        self.description = description

class BaseTask(ValueObject):

    """
    Base class for tasks.
    Contains an id, title, start time and deadline, and also checkpoint collection.
    """

    def __init__(self, task_id, title, checkpoints):
        if isinstance(task_id, RaceID):
            self.id = task_id
        elif isinstance(task_id, (str, unicode)):
            self.id = RaceID.fromstring(task_id)
        else:
            raise TypeError('Unexpected task id: {}'.format(task_id))
        self._check_checkpoints(checkpoints)
        st, et = times_from_checkpoints(checkpoints)
        self._check_timelimits(st, et)
        self.start_time = st
        self.deadline = et
        self._check_title(title)
        self._title = title
        self._checkpoints = checkpoints

    def _check_timelimits(self, start_time, deadline):
        for i, t in enumerate([start_time, deadline]):
            try:
                datetime.datetime.fromtimestamp(t)
            except TypeError:
                raise TypeError("Expected int or float for timestamp, got {} instead".format(
                    type(t)))
        if start_time >= deadline:
            raise ValueError(
                'Incorrect time section specified: first time value should be before the last')

    def _check_checkpoints(self, checkpoints):
        if not checkpoints:
            raise ValueError("Race can't be created without checkpoints.")
        for chp in checkpoints:
            if not isinstance(chp, Checkpoint):
                raise TypeError("Wrong checkpoint type: {}".format(type(chp)))

    def _check_title(self, title):
        if not isinstance(title, (str, unicode)) or len(title.strip()) == 0:
            raise ValueError('Expection non-zero-length string, got {} instead'.format(
                title))

    def is_task_correct(self):
        try:
            self._check_timelimits(self.start_time, self.deadline)
            self._check_checkpoints(self._checkpoints)
            self._check_title(self._title)
        except (ValueError, TypeError):
            return False
        return True

    @property
    def checkpoints(self):
        return self._checkpoints

    @checkpoints.setter
    def checkpoints(self, value):
        self._check_checkpoints(value)
        st, et = times_from_checkpoints(value)
        self._check_timelimits(st, et)
        self.start_time = st
        self.deadline = et
        self._checkpoints = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._check_title(value)
        self._title = value.strip()

    def __eq__(self, other):
        return self.id == other.id and self.title == other.title \
            and self.checkpoints == other.checkpoints \
            and self.start_time == other.start_time \
            and self.deadline == other.deadline


class SpeedRunTask(BaseTask):
    type = 'speedrun'

    def __init__(self, window_open, window_close, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)
        self._check_window_bounds(window_open, window_close)
        self.window_open = window_open
        self.window_close = window_close

    def is_task_correct(self):
        if not BaseTask.is_task_correct(self):
            return False
        try:
            self._check_window_bounds(self.window_open, self.window_close)
        except (ValueError, TypeError):
            return False
        return True

    def _check_window_bounds(self, window_open, window_close):
        self._check_timelimits(window_open, window_close)
        if window_open < self.start_time or window_close >= self.deadline:
            raise ValueError('Window margins ({}, {}) are out of task bounds ({}, {})'.format(
                window_open, window_close, self.start_time, self.deadline))

    def __eq__(self, other):
        return BaseTask.__eq__(self, other) and self.window_open == other.window_open \
            and self.window_close == other.window_close


class RaceToGoalTask(BaseTask):
    type = 'racetogoal'

    def __init__(self, window_open, window_close,
                 race_gates_number=1, race_gates_interval=None, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)
        self._check_window_bounds(window_open, window_close)
        self.window_open = window_open
        self.window_close = window_close

        self._check_gates(race_gates_number, race_gates_interval)
        self.race_gates_number = race_gates_number
        self.race_gates_interval = race_gates_interval

    def _check_window_bounds(self, window_open, window_close):
        self._check_timelimits(window_open, window_close)
        if window_open < self.start_time or window_close >= self.deadline:
            raise ValueError('Window margins ({}, {}) are out of task bounds ({}, {})'.format(
                window_open, window_close, self.start_time, self.deadline))

    def _check_gates(self, num, interval):
        if not isinstance(num, int) or num < 0:
            raise TypeError('Number of gates must be positive integer')
        if num == 1 and interval is not None:
            raise ValueError('Only one gate specified, expecting null interval: got {} instead'.format(
                interval))
        if num != 1 and (not interval or not isinstance(interval, int) or interval < 0):
            raise ValueError('Multiple gates specified, expecting positive integer interval: got {} instead'.format(
                interval))

    def is_task_correct(self):
        if not BaseTask.is_task_correct(self):
            return False
        try:
            self._check_window_bounds(self.window_open, self.window_close)
            self._check_gates(self.race_gates_number, self.race_gates_interval)
        except (ValueError, TypeError):
            return False
        return True

    def __eq__(self, other):
        return BaseTask.__eq__(self, other) and self.window_open == other.window_open \
            and self.window_close == other.window_close \
            and self.race_gates_number == other.race_gates_number \
            and self.race_gates_interval == other.race_gates_interval


class OpenDistanceTask(BaseTask):
    type = 'opendistance'

    def __init__(self, bearing, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)
        self._check_bearing(bearing)
        self.bearing = bearing

    def _check_bearing(self, bearing):
        if not isinstance(bearing, int) or not 0 <= bearing <= 360:
            raise ValueError("Bearing should be integer from 0 to 360")

    def is_task_correct(self):
        if not BaseTask.is_task_correct(self):
            return False
        try:
            self._check_bearing(self.bearing)
        except ValueError:
            return False
        return True

    def __eq__(self, other):
        return BaseTask.__eq__(self, other) and self.bearing == other.bearing