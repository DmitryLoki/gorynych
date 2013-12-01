'''
DDD-model specific base classes.
'''
import time
import uuid


from zope.interface import implementer
from zope.interface.verify import verifyObject

from gorynych.eventstore.interfaces import IEvent

__author__ = 'Boris Tsema'


# TODO: implement comparison by properties
class ValueObject(object):
    '''
    Base class for value objects.
    '''
    def __setattr__(self, name, value):
        '''
        Make all properties and attributes which doesn't starts with _
        read-only.
        '''
        name_is_readonly = not ( name.startswith('_') or
                                 callable(getattr(self, name, None)))
        name_was_set = hasattr(self, name)
        if name_is_readonly and name_was_set:
            raise AttributeError("ValueObjects  properties are readonly.")
        object.__setattr__(self, name, value)


class DomainIdentifier(object):
    '''
    Base class for aggregate IDs. By default use uuid4 as id.
    '''

    def __init__(self, identifier=None):
        '''
        @param identifier: identifier can be passed on creation.
        @type identifier: DomainIdentifier subclass or string.
        '''
        if identifier is None:
            self._id = self._create_new_id()
        elif identifier.__class__ == self.__class__ and (
            self._string_is_valid_id(str(identifier))
        ):
            self._id = identifier
        elif isinstance(identifier, str):
            if self._string_is_valid_id(identifier):
                self._id = identifier
        else:
            raise ValueError("Got identifier %s with type %s" %
                             (identifier, type(identifier)))

    def _create_new_id(self):
        return str(uuid.uuid4())

    @property
    def id(self):
        return str(self._id)

    @classmethod
    def fromstring(cls, string):
        # deprecated. TODO: delete this method from code.
        id = cls()
        if id._string_is_valid_id(str(string)):
            id._id = str(string)
            return id

    def _string_is_valid_id(self, string):
        try:
            uuid.UUID(string)
        except ValueError as error:
            raise ValueError("Bad id string %r: %r" % (string, error))
        return True

    def __eq__(self, other):
        '''
        Make object comparable by id.
        '''
        if issubclass(other.__class__, DomainIdentifier):
            another = str(other.id)
        else:
            another = str(other)
        return str(self._id) == another

    def __ne__(self, other):
        if issubclass(other.__class__, DomainIdentifier):
            another = str(other.id)
        else:
            another = str(other)
        return str(self._id) != another

    def __hash__(self):
        '''
        Make DomainIdentifier hashable.
        '''
        return hash(self._id)

    def __repr__(self):
        '''
        Make object human-readable in logs.
        '''
        return self._id

    def __str__(self):
        '''
        Make the usage of ID more comfort.
        Id value can be received by str(DomainIdentifier instance)
        '''
        return str(self._id)

    def __len__(self):
        return len(str(self._id))


class AggregateRoot(object):
    '''
    Base class for aggregate roots.
    '''
    _id = None
    def __init__(self):
        self.events = []

    def apply(self, elist=None):
        '''
        Read events list and apply them to self.
        @param elist: list of events.
        @type elist: C{list}
        '''
        if elist:
            assert isinstance(elist, list), "I expect list not a %s" % type(elist)
            for ev in elist:
                if verifyObject(IEvent, ev):
                    evname = ev.__class__.__name__
                    if hasattr(self, 'apply_' + evname):
                        getattr(self, 'apply_' + evname)(ev)
                    else:
                        # For cases when event handled in aggregate's
                        # boundary.
                        self.events.append(ev)


@implementer(IEvent)
class DomainEvent(object):
    '''
    Base class for domain events.
    '''

    serializer = None

    def __init__(self, aggregate_id, payload=None, aggregate_type=None,
                 occured_on=None):
        self.aggregate_id = str(aggregate_id)
        if aggregate_type:
            self.aggregate_type = aggregate_type
        elif issubclass(aggregate_id.__class__, DomainIdentifier):
            self.aggregate_type = aggregate_id.__class__.__name__[:-2].lower()
        else:
            raise ValueError("Provide aggregate_type or instance of "
                             "DomainIdentifier subclass as id.")
        if occured_on:
            self.occured_on = int(occured_on)
        else:
            self.occured_on = int(time.time())

        self.payload = payload

    def __eq__(self, other):
        return self.occured_on == other.occured_on and (
            self.aggregate_id == other.aggregate_id) and (
            self.payload == other.payload) and (
            self.aggregate_type == other.aggregate_type)

    def __ne__(self, other):
        return self.occured_on != other.occured_on or (
            self.aggregate_id != other.aggregate_id) or (
            self.payload != other.payload) or (
            self.aggregate_type != other.aggregate_type)

    def __repr__(self):
        try:
            payload = repr(self.payload)
        except Exception:
            payload = ''
        return '<DomainEvent: name=%s, aggregate_id=%s, aggregate_type=%s, ' \
               'occured_on=%s, payload=%s >' % (self.__class__.__name__,
                self.aggregate_id, self.aggregate_type, self.occured_on,
                payload)

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        '''
        Represent event as string which can be jsonifyed in a dict with keys
         equal to column names in EventStore PostgreSQL realization.
        '''
        result = dict(event_name=self.__class__.__name__,
                      aggregate_id=self.aggregate_id,
                      aggregate_type=self.aggregate_type,
                      event_payload=repr(self.payload),
                      occured_on=self.occured_on)
        return str(result)
