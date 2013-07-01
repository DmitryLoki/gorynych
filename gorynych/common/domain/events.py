# coding=utf-8
from gorynych.common.domain.model import DomainEvent
from gorynych.common.infrastructure import serializers


#### Race events ##############################

class ArchiveURLReceived(DomainEvent):
    '''
    Notify processing system that new archive with tracks has been loaded for
    race.
    Event fields:
    @param id: Race id
    @param url: url with track archive.
    '''
    serializer = serializers.StringSerializer()


class TrackArchiveUnpacked(DomainEvent):
    '''
    Fired in L{gorynych.processor.services.trackservise.ProcessorService}
    @param id: Race ID
    @payload:
        ([{person_id, trackfile, contest_number}, ...], - list of dicts
        [extra trackfile,], - list of str
         [person_id without tracks,]) - list of str
         finded tracks for persons,
         extra tracks,
        paragliders without tracks.
    '''
    serializer = serializers.JSONSerializer()


class ParagliderFoundInArchive(DomainEvent):
    '''
    Person found in track archive.
    @param id: RaceID
    @param payload: {person_id, trackfile, contest_number}
    '''
    serializer = serializers.JSONSerializer()


class RaceGotTrack(DomainEvent):
    '''
    Fired when first data for new track has been received.
    @param aggregate_id: RaceID
    @param payload: {contest_number, track_type, track_id}
    '''
    serializer = serializers.JSONSerializer()


class TrackArchiveParsed(DomainEvent):
    '''
    All tracks from track archive parsed and saved.
    @param aggregate_id: RaceID
    @param payload: None
    '''
    serializer = serializers.StringSerializer()


class RaceCheckpointsChanged(DomainEvent):
    '''
    Notify other systems (such as processor) about checkpoints change.
    @todo: think about more explicit name for this event.
    Event fields:
    @param id: Race id
    @param payload: list with new checkpoints. List of L{Checkpoints}.
    '''
    from gorynych.common.domain.types import checkpoint_from_geojson
    serializer = serializers.GeoObjectsListSerializer(checkpoint_from_geojson)


class TrackWasNotParsed(DomainEvent):
    '''
    For some reason (error mostly) track wasn't parsed.
    @param aggregate_id: RaceID
    @param payload:{contest_number, reason}
    '''
    serializer = serializers.JSONSerializer()


###### Track events #############################
class TrackCreated(DomainEvent):
    '''
    Fired when track need to be created.
    @param aggregate_id: TrackID
    @param payload: {race_task, track_type}
    '''
    serializer = serializers.JSONSerializer()


class TrackCheckpointTaken(DomainEvent):
    '''
    Fired then pilot took checkpoint.
    @param aggregate_id: TrackID
    @param payload: (checkpoint number, dist from pilot to checkpoint).
    '''
    serializer = serializers.TupleOf(serializers.IntSerializer())


class TrackStarted(DomainEvent):
    '''
    Fired then system decided that competition has been started.
    @param aggregate_id: TrackID
    '''
    serializer = serializers.NoneSerializer()


class PointsAddedToTrack(DomainEvent):
    '''
    Fired after points processing.
    @param aggregate_id: TrackID.
    @param payload: array with track points which are considered to be a part of track.
    '''
    serializer = serializers.PickleSerializer()


class TrackFinishTimeReceived(DomainEvent):
    '''
    Fired then system found time which will be used as finish time.
    @param aggregate_id: TrackID
    @param payload: finishtime.
    '''
    serializer = serializers.IntSerializer()


class TrackFinished(DomainEvent):
    '''
    Fired then system decided that competition track finished.
    @param aggregate_id: TrackID
    @param payload: None
    '''
    serializer = serializers.NoneSerializer()


class TrackEnded(DomainEvent):
    '''
    Track ended. Pilot landed or finished or time is gone.
    @param aggregate_id: Track ID
    @param payload: track state
    '''
    serializer = serializers.JSONSerializer()


class TrackDataReceived(DomainEvent):
    '''
    Contain data for processing.
    @param payload:{c(coords - lat, lon, alt string), s(device_id string),
    t, gs(ground speed)}
    '''
    serializer = serializers.JSONSerializer()


class TrackInAir(DomainEvent):
    '''
    Появляется когда пилот взлетел
    @param payload: None
    '''
    serializer = serializers.NoneSerializer()


class TrackSpeedExceeded(DomainEvent):
    '''
    Скорость трека стала больше пороговой.
    '''
    serializer = serializers.NoneSerializer()


class TrackSlowedDown(DomainEvent):
    '''
    Скорость трека стала меньше пороговой.
    '''
    serializer = serializers.NoneSerializer()


class TrackLanded(DomainEvent):
    serializer = serializers.NoneSerializer()




########## Person events ##################################
class PersonGotTrack(DomainEvent):
    '''
    Fired then track created for person. Track can be empty or invalid, this event only indicate that system tried to create track.
    @param aggregate_id: PersonID
    @param payload: TrackID
    '''
    serializer = serializers.StringSerializer()


class ParagliderRegisteredOnContest(DomainEvent):
    '''
    Person with id id registered on contest with id contest_id as paraglider.
    Event is fired to notificate users.
    Event fields:
    @param aggregate_id: PersonID
    @param payload: ContestID
    '''
    serializer = serializers.DomainIdentifierSerializer('ContestID')


class TrackerAssigned(DomainEvent):
    '''
    This event is fired then tracker is assigned to someone.

    Event fields are:
    @param aggregate_id: id of aggregate to which tracker has been assigned (
    Person,
    Transport).
    @param payload: (tracker_id, contest_id).
    '''
    serializer = serializers.TupleOf(serializers.StringSerializer())


class TrackerUnAssigned(DomainEvent):
    '''
    This event is fired then tracker is unassigned from person or transport.
    @param aggregate_id: id of aggregate from which tracker has been
    unassigned (Person, Transport).
    @param payload: (tracker_id, contest_id)
    '''
    serializer = serializers.TupleOf(serializers.StringSerializer())

######### Contest events #################################


class ContestRaceCreated(DomainEvent):
    '''
    Fired then race created for contest.
    @param aggregate_id: ContestID
    @param payload: RaceID
    '''
    serializer = serializers.DomainIdentifierSerializer('RaceID')

