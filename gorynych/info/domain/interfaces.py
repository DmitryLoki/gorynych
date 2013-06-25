from zope.interface import Interface


class IRepository(Interface):
    '''
    Aggregate repository.
    '''

    def get_by_id(id):
        '''
        Return aggregate by it's identificator.
        @param id: aggregate id
        @type id: subclass of DomainIdentifier
        @return: aggregate
        @rtype: subclass of AggregateRoot.
        '''

    def save(obj):
        '''
        Save object to repository.
        @param obj:
        @type obj: subclass of AggregateRoot.
        @return: obj
        @rtype:
        '''


class ITrackerRepository(IRepository): pass