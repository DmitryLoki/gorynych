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

    def get_contest_id_for_retrieve_id(self, retrieve_id):
        '''
        Return token for application udid.
        @param retrieve_id:
        @type retrieve_id:
        @return: person_id
        @rtype: C{str}
        '''
        d = self.pool.runQuery(pe.select('id_for_retrieve', 'contest'),
            (retrieve_id,))
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

