'''
Contest Aggregate.
'''
from copy import deepcopy
import datetime
from collections import defaultdict

import pytz

from gorynych.info.domain import transport
from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.common.domain.types import Address, Country, Phone, Checkpoint, MappingCollection, TransactionalDict, Title
from gorynych.common.domain.events import ParagliderRegisteredOnContest
from gorynych.common.infrastructure import persistence
from gorynych.info.domain.ids import ContestID, RaceID, PersonID
from gorynych.common.exceptions import DomainError
from gorynych.common.domain.services import times_from_checkpoints

ROLES = dict(organizer='organizers', staff='staff', winddummy='winddummies',
    paraglider='paragliders')
def _pluralize(role):
    plural_roles = dict(organizer='organizers', staff='staff',
        winddummy='winddummies', paraglider='paragliders')
    result = plural_roles.get(role)
    if result is None:
        raise ValueError("Can't pluralize %s" % role)
    return result


class ContestFactory(object):
    def create_contest(self, title, start_time, end_time, contest_place,
            contest_country, hq_coords, timezone, contest_id=None):
        address = Address(contest_place, contest_country, hq_coords)
        if end_time < start_time:
            raise ValueError("Start time must be less then end time.")
        if not contest_id:
            contest_id = ContestID()
        if not timezone in pytz.all_timezones_set:
            raise pytz.exceptions.UnknownTimeZoneError("Wrong timezone.")
        contest = Contest(contest_id, start_time, end_time, address, title)
        contest.timezone = timezone
        return contest

######################## Contest invariants #######################
def contest_numbers_are_unique(obj):
    '''
    Every paragliders should has unique contest number. If it's not so
    DomainError will be raised.
    @param obj:
    @type obj: Contest
    @raise: DomainError
    '''
    cnums = set(obj.paragliders.get_attribute_values('contest_number'))
    if not len(obj.paragliders) == len(cnums):
        raise DomainError("Every paraglider should have unique contest "
                          "number.")


def person_only_in_one_role(cont):
    '''
    Check if newly added participant already exist as another role.
    @param cont: contest for check
    @type cont: L{Contest}
    @raise: DomainError.
    '''
    counts = defaultdict(list)
    for role in ROLES.values():
        for p_id in getattr(cont, role).keys():
            counts[p_id].append(role)
            if len(counts[p_id]) > 1:
                raise DomainError("%s with id %s already exist as %s" % (
                            role.capitalize(), str(p_id), counts[p_id][0]))


###################################################################

class Contest(AggregateRoot):
    def __init__(self, contest_id, start_time, end_time, address, title):
        super(Contest, self).__init__()
        self.id = ContestID(contest_id)
        self.title = Title(title)
        self._timezone = ''
        self._start_time = start_time
        self._end_time = end_time
        self.address = Address(address)
        self._participants = dict()
        self.retrieve_id = None
        self._tasks = dict()
        self.organizers = MappingCollection()
        self.paragliders = MappingCollection()
        self.winddummies = MappingCollection()
        self.staff = MappingCollection()

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
        try:
            self.check_invariants()
        except DomainError as e:
            self._start_time = old_start_time
            raise e

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        if int(value) == self.end_time:
            return
        old_end_time = self.end_time
        self._end_time = int(value)
        try:
            self.check_invariants()
        except DomainError as e:
            self._end_time = old_end_time
            raise e

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
            raise TypeError(
                'Expected BaseTask instance, got {} instead'.format(type(task)))
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
            if not self.check_invariants():
                self._start_time = old_start_time
                self._end_time = old_end_time
                raise ValueError("Times values violate aggregate's "
                                 "invariants.")

    def check_invariants(self):
        """
        Check next invariants for contest:
        every paraglider has unique contest_number
        context start_time is less then end_time
        person can be only in one role
        not implemented:
        tasks are not overlapping
        """
        contest_numbers_are_unique(self)
        person_only_in_one_role(self)
        end_after_start = int(self.start_time) < int(self.end_time)

        assert end_after_start, "Start time must be before end time."


# Meta adding
for role in ROLES:
    def create_adder_for(role):
        def add_role(self, obj):
            with TransactionalDict(getattr(self, ROLES[role])) as td:
                td[obj.id] = obj
                self.check_invariants()
            if role == 'paraglider':
                persistence.event_store().persist(
                    ParagliderRegisteredOnContest(obj.id, self.id))
            return self
        return add_role
    setattr(Contest, 'add_' + role, create_adder_for(role))

    def create_replacer_for(role):
        def replace_role(self, _id, obj):
            with TransactionalDict(getattr(self, ROLES[role])) as td:
                td[_id] = obj
                self.check_invariants()
        return replace_role
    setattr(Contest, 'replace_' + role, create_replacer_for(role))


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


def change_participant(cont, role, part_id, **data):
    '''
    Change data for contest participant with id as role.
    @param cont: contest for which data should be changed.
    @type cont:  C{Contest}
    @param role: role name (organizer, paraglider, staff, winddummy)
    @type role: C{str}
    @param part_id: participant id
    @type id: C{gorynych.common.model.DomainIdentifier} subclass
    @param data:
    @type data:
    @return: contest with changed role.
    @rtype: C{Contes}
    '''
    if len(data) == 0:
        return cont
    role = role.lower()
    if not part_id in getattr(cont, _pluralize(role)):
        raise ValueError(
            "Participant with id %s wasn't found as %s for contest %s" % (
                part_id, role, cont.id))
    old = getattr(cont, _pluralize(role))[part_id]
    if role == 'organizer':
        new = Organizer(part_id, data.get('email', old.email),
            data.get('name', old.name),
            data.get('description', old.description))
    elif role == 'paraglider':
        new = Paraglider(part_id, data.get('contest_number', old.contest_number),
            data.get('glider', old.glider), data.get('country', old.country),
            data.get('name', old.name), data.get('phone', old.phone))
    else:
        raise ValueError("No such role %s" % role)
    getattr(cont, 'replace_' + role)(part_id, new)
    return cont


class Staff(ValueObject):
    types = frozenset(['rescuer', 'ambulance']).union(transport.TYPES)

    def __init__(self, title, type, description="", phone=None, id=None):
        if type not in self.types:
            raise TypeError(
                'Incorrect type ({}). Avaliable types: {}'.format(
                              type, self.types))
        self.title = title
        self.type = type
        self.phone = Phone(phone) if phone else ''
        self.id = DomainIdentifier(id) if id else DomainIdentifier()
        self.description = description


class Winddummy(ValueObject):
    def __init__(self, person_id, phone, name):
        self.id = PersonID(person_id)
        self.phone = Phone(phone)
        self.name = name


class Organizer(ValueObject):
    def __init__(self, person_id, email, name, description=None):
        self.id = PersonID(person_id)
        self.email = email
        self.name = name
        self.description = description if description else ''


class Paraglider(ValueObject):
    def __init__(self, person_id, contest_number, glider, country, name,
            phone=None):
        self.id = PersonID(person_id)
        assert int(contest_number) >= 0, "Contest number must be positive."
        self.contest_number = int(contest_number)
        self.name = name
        self.glider = glider.strip().split(' ')[0].lower()
        self.country = Country(country)
        self.phone = Phone(phone) if phone else None


class BaseTask(ValueObject):

    """
    Base class for tasks.
    Contains an id, title, start time and deadline, and also checkpoint collection.
    """

    def __init__(self, task_id, title, checkpoints):
        self.id = RaceID(task_id)
        self.title = Title(title)
        self._check_checkpoints(checkpoints)
        st, et = times_from_checkpoints(checkpoints)
        self._check_timelimits(st, et)
        self.start_time = st
        self.deadline = et
        self._checkpoints = checkpoints

    def _check_timelimits(self, start_time, deadline):
        for i, t in enumerate([start_time, deadline]):
            try:
                datetime.datetime.fromtimestamp(t)
            except TypeError:
                raise TypeError(
                    "Expected int or float for timestamp, got {} instead".format(
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

    def is_task_correct(self):
        try:
            self._check_timelimits(self.start_time, self.deadline)
            self._check_checkpoints(self._checkpoints)
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
            raise ValueError(
                'Window margins ({}, {}) are out of task bounds ({}, {})'.format(
                    window_open, window_close, self.start_time, self.deadline))

    def __eq__(self, other):
        return BaseTask.__eq__(self, other) and self.window_open == other.window_open \
            and self.window_close == other.window_close


class RaceToGoalTask(BaseTask):
    type = 'racetogoal'

    def __init__(self, window_open, window_close, race_gates_number=1,
            race_gates_interval=None, *args, **kwargs):
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
            raise ValueError(
                'Window margins ({}, {}) are out of task bounds ({}, {})'.format(
                    window_open, window_close, self.start_time, self.deadline))

    def _check_gates(self, num, interval):
        if not isinstance(num, int) or num < 0:
            raise TypeError('Number of gates must be positive integer')
        if num == 1 and interval is not None:
            raise ValueError(
                'Only one gate specified, expecting null interval: got {} instead'.format(
                    interval))
        if num != 1 and (
                    not interval or not isinstance(interval, int) or interval < 0):
            raise ValueError(
                'Multiple gates specified, expecting positive integer interval: got {} instead'.format(
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