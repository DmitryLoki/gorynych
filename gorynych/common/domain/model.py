'''
DDD-model specific base classes.
'''
import time
import uuid
import simplejson as json


from zope.interface import implementer

from gorynych.common.infrastructure.messaging import DomainEventsPublisher
from gorynych.eventstore.interfaces import IEvent

__author__ = 'Boris Tsema'


# TODO: implement comparison by properties
class ValueObject(object):
    '''
    Base class for value objects.
    '''
    pass


class IdentifierObject(object):
    '''
    Base class for aggregate IDs. By default use uuid4 as id.
    '''

    def __init__(self):
        self._id = str(uuid.uuid4())

    @property
    def id(self):
        return str(self._id)

    @classmethod
    def fromstring(cls, string):
        id = cls()
        if id._string_is_valid_id(str(string)):
            id._id = str(string)
            return id

    def _string_is_valid_id(self, string):
        try:
            uuid.UUID(string)
        except ValueError as error:
            raise ValueError("Bad id string: %r" % error)
        return True

    def __eq__(self, other):
        '''
        Make object comparable by id.
        '''
        if issubclass(other.__class__, IdentifierObject):
            another = str(other.id)
        else:
            another = str(other)
        return str(self._id) == another

    def __ne__(self, other):
        if issubclass(other.__class__, IdentifierObject):
            another = str(other.id)
        else:
            another = str(other)
        return str(self._id) != another

    def __hash__(self):
        '''
        Make IdentifierObject hashable.
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
        Id value can be received by str(IdentifierObject instance)
        '''
        return str(self._id)

    def __len__(self):
        return len(str(self._id))


class AggregateRoot(object):
    '''
    Base class for aggregate roots.
    '''
    event_publisher = DomainEventsPublisher()
    _id = None


@implementer(IEvent)
class DomainEvent(object):
    '''
    Base class for domain events.
    '''
    def __init__(self, aggregate_id, payload, aggregate_type=None,
                 occured_on=None):
        self.aggregate_id = str(aggregate_id)
        if aggregate_type:
            self.aggregate_type = aggregate_type
        elif issubclass(aggregate_id.__class__, IdentifierObject):
            self.aggregate_type = aggregate_id.__class__.__name__[:-2].lower()
        else:
            raise ValueError("Provide aggregate_type or instance of "
                             "IdentifierObject subclass as id.")
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

    def __str__(self):
        '''
        Represent event as string which can be jsonifyed in a dict with keys
         equal to column names in EventStore PostgreSQL realization.
        @return: a string which can be dumped by json.
        @rtype: C{str}
        '''
        result = dict(event_name=self.__class__.__name__,
                      aggregate_id=self.aggregate_id,
                      aggregate_type=self.aggregate_type,
                      event_payload=self._payload_to_bytes(),
                      occured_on=self.occured_on)
        return json.dumps(result)

    def _payload_to_bytes(self):
        '''
        Represent event payload as bytes for serialization purpose.
        Reload this method if event payload can't be simply represented by
        bytes(payload).
        @return:
        @rtype:
        '''
        if isinstance(self.payload, bytes):
            return bytes(self.payload)
        elif issubclass(self.payload.__class__, IdentifierObject):
            return bytes(str(self.payload))
        elif isinstance(self.payload, dict):
            return bytes(json.dumps(self.payload))
        elif isinstance(self.payload, int):
            return bytes(self.payload)


