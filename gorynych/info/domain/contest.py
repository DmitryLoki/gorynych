'''
Contest Aggregate.
'''
from gorynych.common.domain.model import IdentifierObject, AggregateRoot
from gorynych.common.domain.types import Address

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