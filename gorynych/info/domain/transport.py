'''
Transport Aggregate.
'''

from gorynych.common.domain.model import AggregateRoot
from gorynych.common.exceptions import DomainError
from gorynych.info.domain.ids import TransportID

import re

# Allowed transport types
TYPES = frozenset(['bus', 'car', 'motorcycle', 'helicopter', 'van'])

class Transport(AggregateRoot):
    def __init__(self, transport_id, title, description=None):
        super(Transport, self).__init__()
        self.id = transport_id
        self._type = None
        self.title = title
        self.description = description
        self._phone = ''

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        value = value.strip().lower()
        if not value in TYPES:
            raise DomainError("Only next types of transport allowed: %s" %
                              TYPES)
        self._type = value

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, value):
        if re.match(r'^\+\d+', value):
            self._phone = value
        else:
            raise ValueError("Incorrect phone %s, I'm waiting for phone like"
                             " this: +3123456789")


class TransportFactory(object):

    def create_transport(self, transport_type, title, description=None,
            tr_id=None):
        title = title.strip().capitalize()
        if description:
            description = description.strip().capitalize()

        if not tr_id:
            tr_id = TransportID()
        if not isinstance(tr_id, TransportID):
            tr_id = TransportID.fromstring(tr_id)
        result = Transport(tr_id, title, description)
        if not transport_type:
            raise ValueError("Transport type must be given")
        result.type = transport_type
        return result


def change_transport(tr, params):
    if params.has_key('id'):
        del params['id']
    if params.has_key('_id'):
        del params['_id']
    for key in params:
        setattr(tr, key, params[key])
    return tr