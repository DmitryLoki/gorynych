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


class ITransportRepository(Interface):
    def get_by_id(transport_id):
        '''
        '''
    def save(obj):
        '''
        '''


class IPersonRepository(Interface):

    def get_by_id(id):
        '''
        Return a person with id.
        @param id:
        @type id:
        @return: a person
        @rtype: Person
        '''

    def save(person):
        '''
        Persist person.
        @param person:
        @type person: Person
        @return:
        @rtype:
        '''

    def get_list(limit, offset):
        '''
        Return list of a person
        '''


class IRaceRepository(Interface):
    def get_by_id(id):
        '''

        @param id:
        @type id:
        @return:
        @rtype:
        '''

    def save(obj):
        '''

        @param obj:
        @type obj:
        @return:
        @rtype:
        '''


class IContestRepository(Interface):
    def get_by_id(id):
        '''

        @param id:
        @type id:
        @return:
        @rtype:
        '''

    def save(obj):
        '''

        @param obj:
        @type obj:
        @return:
        @rtype:
        '''