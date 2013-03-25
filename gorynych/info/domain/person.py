'''
Aggregate Person.
'''
import datetime

from gorynych.common.domain.model import IdentifierObject, AggregateRoot
from gorynych.common.domain.types import Name, Country
from gorynych.info.domain.tracker import TrackerID

MINYEAR = 2012

class PersonID(IdentifierObject):
    '''
    Person identificator is a person e-mail address.
    '''
    pass


class Person(AggregateRoot):

    def __init__(self, name, country, email, regdate):
        self.id = email
        self._name = name
        self._country = country
        self.regdate = regdate
        self.trackers = set()

    @property
    def country(self):
        return self._country.code()

    @property
    def name(self):
        return self._name.full()

    def assign_tracker(self, tracker_id):
        if isinstance(tracker_id, TrackerID):
            self.trackers.add(tracker_id)

    def unassign_tracker(self, tracker_id):
        self.trackers.remove(tracker_id)



class PersonFactory(object):
    def __init__(self, event_publisher):
        self.event_publisher = event_publisher

    def create_person(self, name, surname, country, email, year, month, day):
        '''
        Create an instance of Person aggregate.
        @param name:
        @type name: str
        @param surname:
        @type surname: str
        @param country: 2-digit code of person's country
        @type country: str
        @param email: registration email, it's an id for person.
        @type email: str
        @param year: year of person registration
        @type year: int
        @param month: month of person registration
        @type month: int
        @param day: day of person registration
        @type day: int
        @return: a new person
        @rtype: Person
        '''
        if not MINYEAR <= year <= datetime.date.today().year:
            raise ValueError("Year is out of range")
        person = Person(Name(name, surname),
                        Country(country),
                        PersonID(email),
                        datetime.date(year, month, day))
        person.event_publisher = self.event_publisher
        return person

