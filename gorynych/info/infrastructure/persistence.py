'''
Realization of persistence logic.
'''
from zope.interface.declarations import implements

from gorynych.info.domain.person import IPersonRepository


class PersonRepository(object):
    '''
    Implement collection-like interface of Person aggregate instances.
    '''
    implements(IPersonRepository)
    pass