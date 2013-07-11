'''
Base classes for persistence infrastructure.

Module contain global registry for storing repository instances.
Clients register a repository instance which implement corresponding interface.
For retreiving repository instance client use interface class as id.

'''
from io import BytesIO
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
    '''
    Find CREATE TABLE commands from file witn name fname.sql.
    @return: list of commands or None.
    '''
    with open(sqldir + fname + '.sql', 'r') as f:
        tables = re.findall(r'''(CREATE\s+TABLE\s+[-(),.\s\w\\]*);''',
                            f.read(), re.IGNORECASE)
    return tables


def drop_tables(filename, cascade=True):
    '''
    Find table names which were created in file filename.sql and return
    commands for deleting thos tables if exists.
    @param filename:
    @type filename: C{str}
    @param cascade: Do cascade drop or not (default: True)
    @type cascade: C{boolean}
    @return:
    @rtype: C{list}
    '''
    result = []
    with open(sqldir + filename + '.sql', 'r') as f:
        tables = re.findall(r'CREATE\s+TABLE\s?(if exists)?\s+(\w+)\s?\(',
                            f.read(), re.IGNORECASE)
        if tables:
            for table in tables:
                result.append("DROP TABLE IF EXISTS %s %s;" % (table[1],
                                                'CASCADE' if cascade else ''))
    return result


def insert(name, filename=None):
    '''
    Find sql command which tagged "-- Insert name" from file filename.sql
    If filename isn't providev filename=name.
    @param name:
    @type name: C{str}
    @return: command which insert aggregate
    @rtype: C{str} or C{None}
    '''
    return _operation('insert', name, filename)


def select(name, filename=None):
    '''
    Find sql command which tagged "-- Select name" from file filename.sql
    If filename isn't providev filename=name.
    @param name:
    @type name:
    @param filename:
    @type filename:
    @return:
    @rtype:
    '''
    return _operation('select', name, filename)


def update(name, filename=None):
    return _operation('update', name, filename)


def _operation(name, tagname, filename=None):
    if not filename:
        filename = tagname
    with open(sqldir + filename + '.sql', 'r') as f:
        pattern = r'--\s+' + name + r'\s?' + tagname + \
                  r'''\n\s*([\w()\s.,%="'\*+]*);'''
        command = re.search(pattern, f.read(), re.IGNORECASE)
    return command.group(1)


def np_as_text(data):
    cpy = BytesIO()
    for row in data:
        cpy.write('\t'.join([repr(x) for x in row]) + '\n')
    cpy.seek(0)
    return(cpy)
