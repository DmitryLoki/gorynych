'''
Contest Aggregate.
'''
import uuid
from copy import deepcopy

from zope.interface.interfaces import Interface

from gorynych.common.domain.model import IdentifierObject, AggregateRoot
from gorynych.common.domain.model import ValueObject, DomainEvent
from gorynych.common.domain.types import Address, Name, Country
from gorynych.common.infrastructure import persistence
from gorynych.info.domain.tracker import TrackerID
from gorynych.info.domain.race import RaceID, Race, RACETASKS
from gorynych.info.domain.person import IPersonRepository


class IContestRepository(Interface):
    def get_by_id(id): # @NoSelf
        '''

        @param id:
        @type id:
        @return:
        @rtype:
        '''

    def save(obj): # @NoSelf
        '''

        @param obj:
        @type obj:
        @return:
        @rtype:
        '''



class ContestID(IdentifierObject):
    pass


class ContestFactory(object):

    def __init__(self, event_publisher=None):
        self.event_publisher = event_publisher

    def create_contest(self, id, title, start_time, end_time,
                       contest_place, contest_country, hq_coords):
        address = Address(contest_place, contest_country, hq_coords)
        if not int(start_time) <  int(end_time):
            raise ValueError("Start time must be less then end time.")
        title = title.strip().title()
        if not isinstance(id, ContestID):
            id = ContestID(id)

        contest = Contest(id, title, start_time, end_time, address)
        if self.event_publisher:
            contest.event_publisher = self.event_publisher
        return contest


class ParagliderRegisteredOnContest(DomainEvent):
    def __init__(self, id, contest_id):
        self.contest_id = contest_id
        DomainEvent.__init__(self, id)

    def __eq__(self, other):
        return self.id == other.id and self.timestamp == other.timestamp and (
            self.contest_id == other.contest_id)


class Contest(AggregateRoot):

    def __init__(self, id, title, start_time, end_time, address):
        self.id = id
        self.title = title
        self._start_time = start_time
        self._end_time = end_time
        self.address = address
        self._participants = dict()
        self.race_ids = list()

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
            raise ValueError("Incorrect end_time violate aggregate's "
                             "invariants.")

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
    def paragliders(self):
        result = []
        for key in self._participants.keys():
            if self._participants[key]['role'] == 'paraglider':
                result.append(self._participants[key])
        return result


    def register_paraglider(self, person_id, glider, contest_number):
        paraglider_before = deepcopy(self._participants.get(person_id))

        glider = glider.strip().split(' ')[0].lower()
        self._participants[person_id] = dict(role='paraglider',
            contest_number=int(contest_number), glider=glider)
        if not self._invariants_are_correct():
            self._rollback_register_paraglider(paraglider_before, person_id)
            raise ValueError("Paraglider must have unique contest number.")
        self.event_publisher.publish(ParagliderRegisteredOnContest(
                                                        person_id, self.id))
        return self

    def _invariants_are_correct(self):
        """
        Check next invariants for contest:
        every paraglider has unique contest_number
        """
        contest_numbers = set()
        paragliders = set()
        for key in self._participants.keys():
            if self._participants[key]['role'] == 'paraglider':
                contest_numbers.add(
                    self._participants[key]['contest_number'])
                paragliders.add(key)
        all_contest_numbers_uniq = len(paragliders) == len(contest_numbers)

        end_after_start = self.start_time < self.end_time
        return all_contest_numbers_uniq and end_after_start

    def _rollback_register_paraglider(self, paraglider_before, person_id):
        self._participants[person_id] = paraglider_before

    def new_race(self, race_type, checkpoints, race_title):
        '''
        This is a fabric method which create aggregate Race.
        @param race_type: name of the task type.
        @type race_type: str
        @param checkpoints: list of race checkpoints.
        @type checkpoints: list of Checkpoint
        @param race_title: this is a title for the race
        @type race_title: title
        @return: a new race for contest
        @rtype: Race
        '''
        race_id = RaceID(uuid.uuid4())
        race = Race(race_id)
        race.event_publisher = self.event_publisher
        race_type = ''.join(race_type.strip().lower().split())
        if race_type in RACETASKS.keys():
            race.task = RACETASKS[race_type]()
        else:
            raise ValueError("Unknown race type.")

        race.title = race_title.strip().title()
        race.timelimits = (self.start_time, self.end_time)
        # Here Race is created and we start to fill it with useful
        # information.
        race = self._fill_race_with_paragliders(race)
        race.checkpoints = checkpoints
        # TODO: the same for transport and organizers.
        self.race_ids.append(race_id)
        return race

    def _fill_race_with_paragliders(self, race):
        for key in self._participants.keys():
            if self._participants[key]['role'] == 'paraglider':
                person = persistence.get_repository(IPersonRepository
                                                    ).get_by_id(key)
                if person and person.tracker:
                    race.paragliders[
                      self._participants[key]['contest_number']] = Paraglider(
                        key,
                        person.name,
                        person.country,
                        self._participants[key]['glider'],
                        self._participants[key]['contest_number'],
                        person.tracker)
        return race

    def change_participant_data(self, person_id, **kwargs):
        if not kwargs:
            raise ValueError("No new data has been received.")
        try:
            old_person = deepcopy(self._participants[person_id])
        except KeyError:
            raise ValueError("No person with such id.")

        for key in kwargs.keys():
            if key == 'contest_number':
                kwargs[key] = int(kwargs[key])
            if key == 'glider':
                kwargs[key] = kwargs[key].strip().split(' ')[0].lower()
            self._participants[person_id][key] = kwargs[key]

        if not self._invariants_are_correct():
            self._participants[person_id] = old_person
            raise ValueError("Paraglider must have unique contest number.")


class Paraglider(ValueObject):

    def __init__(self, person_id, name, country, glider, contest_number,
                 tracker_id):
        from gorynych.info.domain.person import PersonID

        if not isinstance(person_id, PersonID):
            person_id = PersonID(person_id)
        if not isinstance(name, Name):
            raise TypeError("Name must be an instance of Name class.")
        if not isinstance(country, Country):
            country = Country(country)
        if not isinstance(tracker_id, TrackerID):
            tracker_id = TrackerID(tracker_id)

        self.person_id = person_id
        self.name = name.short()
        self.country = country.code()
        self.glider = glider.strip().split(' ')[0].lower()
        self.contest_number = int(contest_number)
        self.tracker_id = tracker_id
