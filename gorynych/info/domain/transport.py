'''
Transport Aggregate.
'''

from gorynych.common.domain.model import AggregateRoot
from gorynych.common.exceptions import DomainError
from gorynych.info.domain.ids import TransportID

# Allowed transport types
TYPES = frozenset(['bus', 'car', 'motorcycle', 'helicopter'])

class Transport(AggregateRoot):
    def __init__(self, transport_id, title, description=None):
        super(Transport, self).__init__()
        self.id = transport_id
        self._type = None
        self.title = title
        self.description = description

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
        if not isinstance(description, str):
            raise TypeError("Description has type %s but nees str." % type(
                description))
        result = Transport(tr_id, title, description)
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Got type!", transport_type
        if not transport_type:
            raise ValueError("Transport type must be given")
        result.type = transport_type
        print ">>> transport with type:", result.type
        return result


def change_transport(tr, params):
    if params.has_key('id'):
        del params['id']
    if params.has_key('_id'):
        del params['_id']
    for key in params:
        setattr(tr, key, params[key])
    return tr