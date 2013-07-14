import time

from twisted.internet import defer
from twisted.python import log

from gorynych.common.infrastructure import persistence as pe
from gorynych.common.exceptions import AuthenticationError
from gorynych.common.domain.services import AsynchronousAPIAccessor

API = AsynchronousAPIAccessor()

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
        Check if token can be used for any chatroom and return chatroom or
        empty list.
        @param token: contest_id
        @type token: C{str}
        @return: chatroom id
        @rtype: C{str}
        @raise: AuthenticationError if no chatroom can be found.
        '''
        time_offset = 3600*9
        now = int(time.time())
        try:
            rlist = yield API.get_contest_races(token)
        except Exception as e:
            log.err(
              "Error while looking for race for contest %s at time %s: %r"
                    % (token, now, e))
            raise AuthenticationError()
        if not rlist:
            raise AuthenticationError()
        result = None
        for item in rlist:
            if item['start_time'] < now < item['end_time'] + time_offset:
                result = item
                break
        if result:
            defer.returnValue(result['id'])
        else:
            raise AuthenticationError()

