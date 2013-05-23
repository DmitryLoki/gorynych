from gorynych.common.domain.model import DomainEvent
from gorynych.common.infrastructure import serializers


#### Race events ##############################

class TrackArchiveUnpacked(DomainEvent):
    '''
    Track archive unpacked and analyzed, tracks for paragliders found.
    @param id: Race ID
    @payload: (list of dict with keys (person_id, trackfile),
    list of extra_tracks, list of paragliders without tracks)
    '''
    serializer = 'hmmm, json?'


class ParagliderFoundInArchive(DomainEvent):
    '''
    Person found in track archive.
    @param id: RaceID
    @param payload: (trackfile, race_id)
    '''
    serializer = serializers.TupleOf(serializers.StringSerializer())


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
