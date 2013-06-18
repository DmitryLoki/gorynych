from gorynych.common.infrastructure import persistence as pe

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