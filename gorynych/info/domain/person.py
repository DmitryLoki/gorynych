'''
Aggregate Person.
'''
import datetime

from gorynych.common.domain.model import IdentifierObject, AggregateRoot
from gorynych.common.domain.types import Name, Country
from gorynych.info.domain.tracker import TrackerID

# First registration was occured in 2012 year.
MINYEAR = 2012

# Person can participate in contest with one of this roles.
ROLES = frozenset(['paraglider', 'organizator'])

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
        self._contests = dict()

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

    def participate_in_contest(self, contest_id, role):
        # TODO: does person really need to keep information about contests in which he or she take participatance?
        from gorynych.info.domain.contest import ContestID
        if isinstance(contest_id, ContestID):
            if role in ROLES:
                self._contests[contest_id] = role
            else:
                raise ValueError("Bad role: %s" % role)
        else:
            raise ValueError("Bad contest id. ContestID: %r" % contest_id)

    @property
    def contests(self):
        return self._contests.keys()

    def dont_participate_in_contest(self, contest_id):
        try:
            del self._contests[contest_id]
        except KeyError:
            pass


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

    
class PersonRepository(object):
    @classmethod
    def get_by_id(cls, id):
        pass
