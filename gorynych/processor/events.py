from gorynych.common.domain.model import DomainEvent
from gorynych.common.infrastructure import serializers

class TrackArchiveParsed(DomainEvent):
    '''
    Fired with pickled track data after archive parsing.
    '''
    serializer = serializers.StringSerializer()
