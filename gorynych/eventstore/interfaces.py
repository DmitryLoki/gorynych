from zope.interface import Interface, Attribute


class IAppendOnlyStore(Interface):
    '''
    I'm the store to which is only allowed ot append. I store the events.
    '''
    def load_events(id):
        '''
        Read stored records for aggregate with id
        @param id: aggregate id.
        @type id: C{str}
        @return: None or iterable thing which handle stored records.
        @rtype: C{iterable}
        '''

    def append(serialized_event):
        '''
        Append event to store.
        '''


class IEventStore(Interface):
    '''
    I store events in append-only store. If you need a list of events I can
    give it to you.
    '''

    def load_events(aggregate_id):
        '''
        Load events for aggregate_id.
        @param aggregate_id:
        @type aggregate_id:
        @return:
        @rtype: C{list}
        '''

    def persist(event):
        '''
        I persist event in store. Event must be an implementer of L{IEvent}
        interface.
        @param event: an instance of L{DomainEvent} subclass.
        '''


class IEvent(Interface):
    '''
    I'm an occured event.
    '''
    aggregate_id = Attribute("""Id of aggregate to which I correspond.
    @type aggregate_id: C{str}.""")

    aggregate_type = Attribute("""Aggregate type. @type aggregate_type: C{
    str}""")

    occured_on = Attribute("""Time when event occured. @type occured_on: C{int}""")

    payload = Attribute("""Body of the event. Here can be a C{dict},
    file or something binary.""")