'''
Aggregate Person.
'''
import datetime

from zope.interface.interfaces import Interface

from gorynych.common.domain.model import AggregateRoot
from gorynych.common.domain.types import Name, Country
from gorynych.info.domain.ids import PersonID, TrackerID

# First registration was occured in 2012 year.
MINYEAR = 2012

# Person can participate in contest with one of this roles.
ROLES = frozenset(['paraglider', 'organizator'])

class Person(AggregateRoot):
    def __init__(self, person_id, name, country, email, regdate):
        self.id = person_id
        self.email = email
        self._name = name
        self._country = country
        self.regdate = regdate
        self.tracker = None
        self._contests = dict()

    @property
    def country(self):
        return self._country.code()

    @country.setter
    def country(self, value):
        self._country = Country(value)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, dict):
            TypeError("I'm waiting for a dictionary with name and surname.")
        self._name = Name(name=value.get('name', self._name.name),
                          surname=value.get('surname', self._name.surname))

    def assign_tracker(self, tracker_id):
        if isinstance(tracker_id, TrackerID):
            self.tracker = tracker_id

    def unassign_tracker(self, tracker_id):
        if not self.tracker == tracker_id:
            raise KeyError("No such tracker.")
        self.tracker = None

    def participate_in_contest(self, contest_id, role):
        # TODO: does person really need to keep information about contests
        # in which he or she take participatance?
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

    def __eq__(self, other):
        return self.id == other.id and (
            self.name.full() == other.name.full()) and (
            self.email == other.email)


class PersonFactory(object):

    def create_person(self, name, surname, country, email, year=None,
                      month=None, day=None, person_id=None):
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
        if not year and not month and not day:
            today = datetime.date.today()
            year, month, day = today.year, today.month, today.day
        year, month, day = int(year), int(month), int(day)
        if not MINYEAR <= year <= datetime.date.today().year:
            raise ValueError("Year is out of range %s-%s" %
                             (MINYEAR, datetime.date.today().year))

        if not person_id:
            person_id = PersonID()
        elif not isinstance(person_id, PersonID):
            person_id = PersonID.fromstring(person_id)
        person = Person(person_id,
                        Name(name, surname),
                        Country(country),
                        email,
                        datetime.date(year, month, day))
        return person


class IPersonRepository(Interface):
    def get_by_id(id):
        '''
        Return a person with id.
        @param id:
        @type id:
        @return: a person
        @rtype: Person
        '''

    def save(person):  # @NoSelf
        '''
        Persist person.
        @param person:
        @type person: Person
        @return:
        @rtype:
        '''

#     def get_list(limit, offset):  # @NoSelf
#         '''
#         Return list of a person 
#         '''
