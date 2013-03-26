'''
Contest Aggregate.
'''
import uuid


from gorynych.common.domain.model import IdentifierObject, AggregateRoot, ValueObject, DomainEvent
from gorynych.common.domain.types import Address, Name, Country
from gorynych.info.domain.tracker import TrackerID
from gorynych.info.domain.race import RaceID, Race, RACETASKS
from gorynych.info.domain.person import PersonRepository

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
        self.start_time = start_time
        self.end_time = end_time
        self.address = address
        self._participants = dict()
        self.races = list()

    def register_paraglider(self, person_id, glider, contest_number):
        paraglider_before = self._participants.get(person_id)

        glider = glider.strip().split(' ')[0].lower()
        self._participants[person_id] = dict(role='paraglider',
            contest_number=int(contest_number), glider=glider)
        if not self._invariants_are_correct():
            self._rollback_register_paraglider(paraglider_before, person_id)
            raise ValueError("Paraglider must have unique contest number.")
        self.event_publisher.publish(ParagliderRegisteredOnContest(
                                                        person_id, self.id))

    def _invariants_are_correct(self):
        """
        Check next invariants for contest:
        every paraglider has unique contest_number
        """
        contest_numbers = set()
        paragliders = set()
        for key in self._participants.keys():
            if self._participants[key]['role'] == 'paraglider':
                contest_numbers.add(self._participants[key]['contest_number'])
                paragliders.add(key)
        all_contest_numbers_uniq = len(paragliders) == len(contest_numbers)
        return all_contest_numbers_uniq

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
        race_type = ''.join(race_type.strip().lower().split())
        if race_type in RACETASKS.keys():
            race.task = RACETASKS[race_type]()
        else:
            raise ValueError("Unknown race type.")

        race.title = race_title.strip().title()
        race.timelimits = (self.start_time, self.end_time)
        # Here Race is created and we start to fill it with useful
        # information.
        race.checkpoints = checkpoints
        # TODO: the same for transport and organizers.
        race = self._fill_race_with_paragliders(race)
        self.races.append(race_id)
        return race

    def _fill_race_with_paragliders(self, race):
        # TODO: repository :), then uncomment this.
#        for key in self._participants.keys():
#            if self._participants[key]['role'] == 'paraglider':
#                person = PersonRepository.get_by_id(key)
#                if len(person.trackers):
#                    race.paragliders.add(Paraglider(
#                        key,
#                        person.name,
#                        person.country,
#                        self._participants[key]['glider'],
#                        self._participants[key]['contest_number'],
#                        person.pop()))
        return race


class Paraglider(ValueObject):

    def __init__(self, person_id, name, country, glider, contest_number,
                 tracker_id):
        from gorynych.info.domain.person import PersonID

        if not isinstance(person_id, PersonID):
            person_id = PersonID(person_id)
        if not isinstance(name, Name):
            raise TypeError("Name must be an instance of Name class.")
        if not isinstance(country, Country):
            raise TypeError("Country must be an instance of Country class.")
        if not isinstance(tracker_id, TrackerID):
            tracker_id = TrackerID(tracker_id)

        self.person_id = person_id
        self.name = name
        self.country = country
        self.glider = glider.strip().split(' ')[0].lower()
        self.contest_number = int(contest_number)
        self.tracker_id = tracker_id
