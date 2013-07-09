# -*- coding: utf-8 -*-
'''
Aggregate Person.
'''
import datetime
import re

from zope.interface.interfaces import Interface

from gorynych.common.domain.model import AggregateRoot
from gorynych.common.domain.types import Name, Country
from gorynych.info.domain.ids import PersonID, TrackerID
from gorynych.info.restui.base_resource import BadParametersError


# Person can participate in contest with one of this roles.
ROLES = frozenset(['paraglider', 'organizator'])


class Person(AggregateRoot):

    def __init__(self, person_id, name, country, email, regdate, person_data):
        super(Person, self).__init__()
        self.id = person_id
        self.email = email
        self._name = name
        self._country = country
        self.regdate = regdate
        # contid:tracker_id
        self.person_data = person_data
        self.trackers = dict()
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

    def apply_TrackerAssigned(self, ev):
        tr, cont = ev.payload
        self.trackers[cont] = tr

    def apply_TrackerUnAssigned(self, ev):
        tr, cont = ev.payload
        del self.trackers[cont]


class PersonFactory(object):
    opt_params = ['phone', 'udid']

    def _validate_phone(self, phone):
        pattern = r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'
        print phone
        m = re.match(pattern, phone)
        if not m:
            print 'here?'
            raise BadParametersError('Phone seems to be not valid.')
        return m.group()

    def _validate_data(self, person_data):
        for data_type in person_data:
            if data_type == 'phone':
                person_data[data_type] = self._validate_phone(person_data[data_type])
            # ... other stuff to validate
        return person_data

    def create_person(self, name, surname, country, email, year=None,
                      month=None, day=None, person_id=None, **person_data):
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
        @return: a new person
        @rtype: Person
        '''
        if not person_id:
            person_id = PersonID()
        elif not isinstance(person_id, PersonID):
            person_id = PersonID.fromstring(person_id)
        person = Person(person_id,
                        Name(name, surname),
                        Country(country),
                        email,
                        datetime.date.today(),
                        self._validate_data(person_data))
        return person


# TODO: move interfaces into domain.interfaces.
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

    def get_list(limit, offset):
        '''
        Return list of a person
        '''


def change_person(person, params):
    new_name = dict()
    if params.get('name'):
        new_name['name'] = params['name']
    if params.get('surname'):
        new_name['surname'] = params['surname']
    person.name = new_name
    if params.get('country'):
        person.country = params['country']

    # other secondary params
    for key in ['phone', 'udid']:
        if key in params:
            person.person_data[key] = params[key]
    return person
