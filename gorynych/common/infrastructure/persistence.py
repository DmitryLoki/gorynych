'''
Base classes for persistence infrastructure.

Module contain global registry for storing repository instances.
Clients register a repository instance which implement corresponding interface.
For retreiving repository instance client use interface class as id.

'''
import os
import re

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


# SQL staff

sqldir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'sql/')

def create_tables(fname):
    with open(sqldir + fname + '.sql', 'r') as f:
        tables = re.findall(r'''(CREATE\s+TABLE\s+[()-,\s\w\\]*);''',
                            f.read(), re.IGNORECASE)
    return tables

def drop_tables(fname, cascade=True):
    result = []
    with open(sqldir + fname + '.sql', 'r') as f:
        tables = re.findall(r'CREATE\s+TABLE\s?(if exists)?\s+(\w+)\s?\(',
                            f.read(), re.IGNORECASE)
        if tables:
            for table in tables:
                result.append("DROP TABLE IF EXISTS %s %s;" % (table[1],
                                                'CASCADE' if cascade else ''))
    return result
