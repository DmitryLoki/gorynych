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
    def __init__(self, id, type, title, description=None):
        self.id = id
        self.type = type
        self.title = title
        self.description = description



class TransportFactory(object):

    def create_transport(self, id, type, title, description=None):
        type = type.strip().lower()
        title = title.strip().capitalize()
        if description:
            description = description.strip().capitalize()

        if not isinstance(id, TransportID):
            id = TransportID(id)
        if not type in TYPES:
            raise ValueError("Unknown transport type.")
        return Transport(id, type, title, description)


