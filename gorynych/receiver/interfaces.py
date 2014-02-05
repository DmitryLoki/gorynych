'''
Interfaces for receiver system.
'''
__author__ = 'Boris Tsema'

from zope.interface import Interface


class IWrite(Interface):
    '''
    I write data somewhere.
    '''
    def write(data):
        '''
        Write data asynchronously.
        @param data:
        @type data:
        @return: Deferred which will fire as None on success.
        @rtype: C{twisted.internet.defer.Deferred}
        '''
