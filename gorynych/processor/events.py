from gorynych.common.domain.model import DomainEvent
from gorynych.common.infrastructure import serializers

class TrackArchiveParsed(DomainEvent):
    '''
    Fired with pickled track data after archive parsing.
    '''
    serializer = serializers.StringSerializer()

class PersonGotTrack(DomainEvent):
    serializer = serializers.StringSerializer()

class TrackAddedToRace(DomainEvent):
    '''
    @param payload: (track_id, contest_number)
    @type: payload: C{tuple}
    '''
    serializer = serializers.TupleOf(serializers.StringSerializer())