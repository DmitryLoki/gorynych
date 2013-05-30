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
    @param payload: {person_id, trackfile, contest_number}
    '''
    serializer = serializers.StringSerializer()


class TrackArchiveParsed(DomainEvent):
    '''
    All tracks from track archive parsed and saved.
    @param aggregate_id: RaceID
    @param payload: None
    '''
    serializer = serializers.StringSerializer()


class RaceTrackCreated(DomainEvent):
    '''
    Fired when first data for new track has been received.
    @param payload: {contest_number, track_type, trackid}
    '''
    serializer = serializers.JSONSerializer()


###### Track events #############################
class TrackCreated(DomainEvent):
    '''
    Fired when track need to be created.
    @param aggregate_id: TrackID
    @param payload: {race_task(checkpoints), track_type}
    '''
    serializer = serializers.JSONSerializer()


class TrackDataReceived(DomainEvent):
    '''
    In offline track fired when track filename is received.
    @param payload: track filename.
    '''
    serializer = serializers.StringSerializer()


class TrackStarted(DomainEvent):
    '''
    New track started.
    @param aggregate_id: TrackID
    @param payload: DomainEvent id from which track starts.
    '''
    serializer = serializers.StringSerializer()


class TrackEnded(DomainEvent):
    '''
    Track ended. Pilot landed or finished or time is gone.
    @param aggregate_id: Track ID
    @param payload: None
    '''
    serializer = serializers.StringSerializer()


########## Person events ##################################
class PersonGotTrack(DomainEvent):
    '''
    Fired then track created for person. Track can be empty or invalid, this event only indicate that system tried to create track.
    @param aggregate_id: PersonID
    @param payload: TrackID
    '''
    serializer = serializers.StringSerializer()


############################

class TrackAddedToRace(DomainEvent):
    '''
    @param payload: (track_id, contest_number)
    @type: payload: C{tuple}
    '''
    serializer = serializers.TupleOf(serializers.StringSerializer())
