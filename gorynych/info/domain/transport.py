'''
Transport Aggregate.
'''
from zope.interface.interfaces import Interface
from gorynych.common.domain.model import IdentifierObject, AggregateRoot


# Allowed transport types
TYPES = frozenset(['bus', 'car', 'helicopter'])


class TransportID(IdentifierObject):
    pass

class ITransportRepository(Interface):
    def get_by_id(transport_id): # @NoSelf
        '''
        '''
    def save(obj): # @NoSelf
        '''
        '''
class Transport(AggregateRoot):
    def __init__(self, transport_id, transport_type, title, description=None):
        self.id = transport_id
        self.type = transport_type
        self.title = title
        self.description = description



class TransportFactory(object):

    def create_transport(self, transport_id, transport_type, title, description=None):
        transport_type = transport_type.strip().lower()
        title = title.strip().capitalize()
        if description:
            description = description.strip().capitalize()

        if not isinstance(transport_id, TransportID):
            transport_id = TransportID(id)
        if not type in TYPES:
            raise ValueError("Unknown transport type.")
        return Transport(id, type, title, description)


