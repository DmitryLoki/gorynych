'''
Created on 30.04.2013

@author: licvidator
'''


class SimpleMemoryStorage(object):

    def __init__(self):
        self._storage = dict()


class ContestInMemoryRepository(object):
    '''
    Хранилище объектов типа Contest
    '''

    def __init__(self):
        '''
        Constructor
        '''
