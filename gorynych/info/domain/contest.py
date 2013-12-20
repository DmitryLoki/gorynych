'''
Contest Aggregate.
'''
from collections import defaultdict, Counter
import simplejson as json

import pytz

from gorynych.info.domain import transport
from gorynych.common.domain.model import AggregateRoot, ValueObject, DomainIdentifier
from gorynych.common.domain.types import Address, Country, Phone, MappingCollection, TransactionalDict, Title, DateRange
from gorynych.common.domain.events import ParagliderRegisteredOnContest
from gorynych.common.infrastructure import persistence
from gorynych.info.domain.ids import ContestID, RaceID, PersonID
from gorynych.common.exceptions import DomainError

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


def contest_times_are_good(cont):
    '''
    Contest should last for some time.
    @param cont: checked contest
    @type cont: Contest
    @raise DomainError
    '''
    if cont.times.is_empty():
        raise DomainError("Contest times are wrong: %r" % cont.times)


def contest_tasks_are_correct(cont):
    '''
    Check if contest tasks can exist in given contest.
    @param cont:
    @type cont: Contest
    @raise DomainError
    '''
    # Contest has paragliders to fly.
    if len(cont.tasks) > 0 and len(cont.paragliders) == 0:
        raise DomainError("No paragliders on contest.")

    # Titles are unique.
    titles = [t.title for t in cont.tasks.values()]
    dup = Counter(titles) - Counter(set(titles))
    if len(dup) > 0:
        raise DomainError("Task titles are duplicated: %s." % dup.keys())

    # Task times inside contest.
    for key, task in cont.tasks.iteritems():
        if not cont.times.overlap(DateRange(task.window_open, task.deadline)):
            raise DomainError("Task %s is out of contest's time range: %s" %
                              (key, cont.times))

    # Tasks times don't overlaps.
    sorted_tasks = sorted(cont.tasks.values(), key=lambda t: t.window_open)
    for i, t in enumerate(sorted_tasks[1:]):
        if DateRange(sorted_tasks[i].deadline, t.window_open).is_empty():
            raise DomainError("Task %s follow immediately after task %s" % (
                t.id, sorted_tasks[i].id))

    # TODO: check trackers existance for live-tracking tasks.


###################################################################

class Contest(AggregateRoot):
    def __init__(self, contest_id, start_time, end_time, address, title):
        super(Contest, self).__init__()
        self.id = ContestID(contest_id)
        self.title = Title(title)
        self.times = DateRange(start_time, end_time)
        self._timezone = ''
        self.address = Address(address)
        self.retrieve_id = None
        self.organizers = MappingCollection()
        self.paragliders = MappingCollection()
        self.winddummies = MappingCollection()
        self.staff = MappingCollection()
        self.tasks = MappingCollection()

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
        return self.times[0]

    @property
    def end_time(self):
        return self.times[1]

    def create_task(self, title, task_type, checkpoints, **kw):
        '''
        Factory method which create task and add it to contest.
        @param title: task title
        @type title: str or Title
        @param task_type: task type in lowercase without spaces
        @type task_type: C{str}
        @param checkpoints: checkpoints in GeoJSON.
        @type checkpoints: C{str} or C{dict}
        @param kw: another useful parameters for task
        @rtype: NoneType
        @raise DomainError, ValueError
        '''
        # Initialize specifications.
        four_points = CheckpointTypesSpecification(['to', 'es', 'ss', 'goal'])
        one_point = CheckpointTypesSpecification(['to'])
        allowed_goals = GoalTypeSpecification(['Point'])
        two_times = TimesSpecification(2)
        four_times = TimesSpecification(4)
        # Dictionary to simplify task checking.
        types = defaultdict(dict)
        types['opendistance']['specifications'] = [
            (one_point, ValueError("Checkpoint's types are incorrect.")),
            (two_times, ValueError("Task is empty")),
            (allowed_goals, ValueError("Goal should be one of %s"
                                       % allowed_goals.goals))
        ]
        types['speedrun']['specifications'] = [
            (four_points, ValueError("Checkpoint's types are incorrect.")),
            (four_times, ValueError("Task times are incorrect")),
            types['opendistance']['specifications'][2]
        ]
        types['racetogoal']['specifications'] = types['speedrun'][
            'specifications']

        # Prepare input parameters.
        task_id = RaceID() if not kw.get('id') else RaceID(kw['id'])
        if task_type == 'opendistance':
            checkpoints = OpenDistanceTask.read_checkpoints(checkpoints)
            bearing = OpenDistanceTask.read_bearing(kw.get('bearing'))
            task = OpenDistanceTask(title, checkpoints, kw['window_open'],
                kw['deadline'], bearing, task_id)
        elif task_type == 'speedrun':
            checkpoints = SpeedRunTask.read_checkpoints(checkpoints)
            window = DateRange(kw['window_open'], kw['window_close'])
            speed_section = DateRange(kw['start_time'], kw['deadline'])
            task = SpeedRunTask(title, checkpoints, window, speed_section,
                task_id)
        elif task_type == 'racetogoal':
            checkpoints = RaceToGoalTask.read_checkpoints(checkpoints)
            window = DateRange(kw['window_open'], kw['window_close'])
            speed_section = DateRange(kw['start_time'], kw['deadline'])
            start_gates_number = int(kw.get('start_gates_number', 1))
            gate_interval = int(kw.get('start_gates_interval', 0))
            task = RaceToGoalTask(title, checkpoints, window, speed_section,
                start_gates_number, gate_interval, task_id)
        else:
            raise ValueError("Unknown task type %s" % task_type)

        # Check created task.
        for spec, exc in types[task_type]['specifications']:
            if not spec.is_satisfied_by(task):
                raise exc
        with TransactionalDict(self.tasks) as tasks:
            tasks[task_id] = task
            self.check_invariants()

    def change_times(self, start_time, end_time):
        '''
        Change both start time and end time of context.
        @param start_time:
        @type start_time: C{int}
        @param end_time:
        @type end_time: C{int}
        @raise: ValueError if times violate aggregate's invariants.
        '''
        old_times = self.times
        self.times = DateRange(start_time, end_time)
        try:
            self.check_invariants()
        except Exception as e:
            self.times = old_times
            raise e

    def check_invariants(self):
        """
        Check next invariants for contest:
        every paraglider has unique contest_number
        person can be only in one role
        not implemented:
        tasks are not overlapping
        """
        contest_numbers_are_unique(self)
        person_only_in_one_role(self)
        contest_times_are_good(self)
        contest_tasks_are_correct(self)


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


######################## Task's stuff ########################################

class CheckpointTypesSpecification(ValueObject):
    '''
    Check does task checkpoints has all necessary types: to, goal, es etc.
    '''
    def __init__(self, types=None):
        # At least 'to' should exist.
        self.types = types if types else ['to']
        self.types.sort()

    def is_satisfied_by(self, task):
        point_types = []
        for ch in task.checkpoints['features']:
            _type = ch['properties'].get('checkpoint_type')
            if _type in self.types:
                point_types.append(_type)
        point_types.sort()
        return self.types == point_types


class GoalTypeSpecification(ValueObject):
    '''
    Check goal geometry.
    '''
    def __init__(self, allowed_goals=None):
        # At least Point should be allowed as geometry.
        self.goals = allowed_goals if allowed_goals else ['Point']

    def is_satisfied_by(self, task):
        for ch in task.checkpoints['features']:
            _type = ch['properties'].get('checkpoint_type')
            if _type == 'goal' and ch['geometry']['type'] in self.goals:
                return True
        # Can I return True if no goals set in task? I think no. So let's
        # return False.
        return False


class TimesSpecification(ValueObject):
    '''
    Check task times: window_open, window_close, start_time, deadline.
    '''
    def __init__(self, times_amount=2):
        # All tasks operate by some amount of times.
        self.times = times_amount

    def is_satisfied_by(self, task):
        if self.times == 2:
            return self._two_times_check(task)
        elif self.times == 4:
            return self._four_times_check(task)
        else:
            raise NotImplementedError("Like Chrome say: Ooops!")

    def _two_times_check(self, task):
        '''
        Two times mean that only window_open and deadline are used.
        @param task:
        @type task:
        @rtype: bool
        '''
        return not DateRange(task.window_open, task.deadline).is_empty()

    def _four_times_check(self, task):
        '''
        Tasks with speedsection.
        @param task:
        @type task:
        @return:
        @rtype:
        '''
        window = DateRange(task.window_open, task.window_close)
        speedsection = DateRange(task.start_time, task.deadline)
        return (not window.is_empty()) and (not speedsection.is_empty()) and (
            task.start_time >= task.window_open)


class BaseTask(ValueObject):
    """
    Base class for tasks.
    """

    @staticmethod
    def read_checkpoints(checkpoints):
        '''
        Check is passed checkpoints string correct.
        @param checkpoints: json with checkpoints.
        @type checkpoints: str
        @return: checked checkpoints
        @rtype: dict
        @raise ValueError
        '''
        # TODO: replace it with validation through json schema.
        if isinstance(checkpoints, str):
            checkpoints = json.loads(checkpoints)
        if isinstance(checkpoints, dict) and len(checkpoints) > 1:
            return checkpoints
        else:
            ValueError("Can't read checkpoints %r" % checkpoints)


class SpeedRunTask(BaseTask):
    def __init__(self, title, checkpoints, window, speedsection, id):
        self.title = Title(title)
        self.checkpoints = checkpoints
        self.window_open, self.window_close = window
        self.start_time, self.deadline = speedsection
        self.id = id

    @staticmethod
    def read_checkpoints(checkpoints):
        # TODO: replace it with validation through json schema.
        checkpoints = BaseTask.read_checkpoints(checkpoints)
        if len(checkpoints['features']) < 2:
            raise ValueError("Too small checkpoints: %r " % checkpoints)
        return checkpoints


class RaceToGoalTask(BaseTask):

    def __init__(self, title, checkpoints, window, speed_section,
            gates_number, gate_interval, id):
        self.title = Title(title)
        self.checkpoints = checkpoints
        self.window_open, self.window_close = window
        self.start_time, self.deadline = speed_section
        self.gates_number = gates_number
        self.gates_interval = gate_interval
        self.id = id
        if self.gates_number > 1 and not self.gates_interval > 0:
            raise ValueError("Gates number is set but gates interval is %s"
                             % self.gates_interval)

    @staticmethod
    def read_checkpoints(checkpoints):
        # TODO: replace it with validation through json schema.
        checkpoints = BaseTask.read_checkpoints(checkpoints)
        if len(checkpoints['features']) < 2:
            raise ValueError("Too small checkpoints: %r " % checkpoints)
        return checkpoints


class OpenDistanceTask(BaseTask):

    def __init__(self, title, checkpoints, window_open, deadline, bearing,
            id):
        self.title = Title(title)
        self.checkpoints = checkpoints
        self.window_open = window_open
        self.deadline = deadline
        self.bearing = bearing
        self.id = id

    @staticmethod
    def read_bearing(bearing):
        if bearing is None:
            return bearing
        if not isinstance(bearing, int) or not 0 <= bearing <= 360:
            raise ValueError("Bearing should be integer from 0 to 360.")
        return bearing

