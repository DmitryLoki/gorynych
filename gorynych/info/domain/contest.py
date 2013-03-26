'''
Contest Aggregate.
'''
from gorynych.common.domain.model import IdentifierObject, AggregateRoot, ValueObject
from gorynych.common.domain.types import Address, Name, Country
from gorynych.info.domain.tracker import TrackerID

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


class Contest(AggregateRoot):

    def __init__(self, id, title, start_time, end_time, address):
        self.id = id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.address = address
        self._participants = dict()


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
