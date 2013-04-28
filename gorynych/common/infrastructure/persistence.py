'''
Base classes for persistence infrastructure.

Module contain global registry for storing repository instances.
Clients register a repository instance which implement corresponding interface.
For retreiving repository instance client use interface class as id.

'''
from gorynych.eventstore.interfaces import IEventStore

global_repository_registry = dict()


def register_repository(interface, repository_instance):
    '''
    Register repository in global registry.
    @param interface:
    @type interface: Interface
    @param repository_instance: instance of repository
    @type repository_instance:
    @return:
    @rtype:
    '''
    global global_repository_registry
    if interface.providedBy(repository_instance):
        global_repository_registry[interface.__name__] = repository_instance

def get_repository(interface):
    '''
    Return repository instance which implement passed interface
    @param interface:
    @type interface: Interface
    @return: repository
    @rtype:
    '''
    return global_repository_registry.get(interface.__name__)


def add_event_store(event_store):
    register_repository(IEventStore, event_store)


def event_store():
    return get_repository(IEventStore)
