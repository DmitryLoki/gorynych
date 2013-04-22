import sys
from zope.interface import Interface

__author__ = 'Boris Tsema'


class IAppendOnlyStore(Interface):
    '''
    I'm the store to which is only allowed ot append. I store the events.
    '''
    def read(id, from_version, to_version):
        '''
        Read stored records for name and in version range.
        @param id:
        @type id: C{str}
        @param from_version:
        @type from_version: C{int}
        @param to_version:
        @type to_version: C{int}
        @return: None or iterable thing which handle stored records.
        @rtype: C{iterable}
        '''

    def append(id, data, expected_version):
        '''
        Append data to store.
        @param id: aggregate id to which I will append data.
        @type id: C{str}
        @param data: payload
        @type data:
        @param expected_version: I will expect this version of data,
        if my expectaion will failed ConcurrencyError will be raised.
        @type expected_version: C{int}
        @return:
        @rtype:
        @raise: ConcurrencyError
        '''


class IEventStore(Interface):
    '''
    I store events in append-only store. If you need a list of events I can
    give it to you.
    '''

    def load_event_stream(id, from_version=0, to_version=sys.maxint):
        '''
        I load events for aggregate with id from the store in range
        from_version:to_version.
        @param id:
        @type id: L{IdentifierObject} subclass
        @param from_version:
        @type from_version: C{int}
        @param to_version:
        @type to_version: C{int}
        @return: event stream
        @rtype: C{list}
        '''
    #
    # def load_events_from_snapshot(id, snapshot_id, max_events=sys.maxint):
    #     '''
    #     TODO: implement it later
    #     @param id: aggregate id for which events will be loaded
    #     @type id: subclass of L{IdentifierObject}
    #     @param snapshot_id: id of snapshot
    #     @type snapshot_id: not implemented yet
    #     @param max_events: number of events to load
    #     @type max_events: C{int}
    #     @return: snapshot and event stream
    #     @rtype: C{tuple}
    #     '''