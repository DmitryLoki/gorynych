import time

from twisted.internet import defer

from gorynych.common.infrastructure import persistence as pe
from gorynych.common.exceptions import AuthenticationError

class AuthenticationService(object):
    def __init__(self, pool):
        self.pool = pool

    def get_udid_token(self, udid):
        '''
        Return token for application udid.
        @param udid:
        @type udid:
        @return: person_id
        @rtype: C{str}
        '''
        d = self.pool.runQuery(pe.select('person_id_by_udid', 'person'),
            (udid,))
        d.addCallback(lambda x: x[0][0])
        return d

    @defer.inlineCallbacks
    def authenticate(self, token):
        '''
        Check if token can be used for any chatroom.
        @param token:
        @type token: C{str}
        @return: chatroom id
        @rtype: C{str}
        @raise: AuthenticationError if no chatroom can be found.
        '''
        time_offset = 3600*5
        t = int(time.time())
        c_id = yield self.pool.runQuery(pe.select('race_id_by_organizator',
            'race'),
            (token, t-time_offset, t+time_offset, t-time_offset, t+time_offset))
        if not c_id:
            raise AuthenticationError()
        defer.returnValue(c_id[0][0])