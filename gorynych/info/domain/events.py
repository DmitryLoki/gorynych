'''
List of domain events in context "info".
TODO: solve dependency problem.
'''
from gorynych.common.domain.model import DomainEvent
from gorynych.common.infrastructure import serializers


#### Race events #####################################

class ArchiveURLReceived(DomainEvent):
    '''
    Notify processing system that new archive with tracks has been loaded for
    race.
    Event fields:
    @param id: Race id
    @param url: url with track archive.
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


#### Person events ######################################


class ParagliderRegisteredOnContest(DomainEvent):
    '''
    Person with id id registered on contest with id contest_id as paraglider.
    Event is fired to notificate users.
    Event fields:
    @param aggregate_id: PersonID
    @param payload: ContestID
    '''
    serializer = serializers.DomainIdentifierSerializer('ContestID')


### Contest events ###################################

class ContestRaceCreated(DomainEvent):
    '''
    Fired then race created for contest.
    @param aggregate_id: ContestID
    @param payload: RaceID
    '''
    serializer = serializers.DomainIdentifierSerializer('RaceID')


###########################################
class TrackerAssigned(DomainEvent):
    '''
    This event is fired then tracker is assigned to someone.

    Event fields are:
    @param id: id of aggregate to which tracker has been assigned (Person,
    Transport).
    @param tracker_id: tracker id.
    '''


class TrackerUnAssigned(DomainEvent):
    '''
    This event is fired then tracker is unassigned from person or transport.
    @param aggregate_id: id of aggregate from which tracker has been
    unassigned (Person, Transport).
    @param payload: id of Tracker aggregate.
    '''
