import json

__author__ = 'Boris Tsema'

from zope.interface import Interface, implementer
from twisted.application.service import Service

from gorynych.chat.domain.model import MessageFactory


class IChatService(Interface):
    '''
    Chat service.
    '''
    def post_message(chatroom, msg):
        '''
        Receive new message for chatroom.
        @param chatroom:
        @type chatroom: C{str}
        @param msg: dictionary with message fields
        @type msg: C{dict}
        @return: message identificator in DB.
        @rtype: C{int}
        '''

    def get_messages(chatroom, from_time, to_time):
        '''
        Return messages from service.
        @param chatroom:
        @type chatroom:
        @param from_time:
        @type from_time:
        @param to_time:
        @type to_time:
        @return:
        @rtype: C{list}
        '''


@implementer(IChatService)
class ChatApplication(Service):
    factory = MessageFactory()

    def __init__(self, repo, auth_service):
        '''

        @param repo:
        @type repo:
        @param auth_service:
        @type auth_service: C{gorynych.chat.domain.services
        .AuthenticationService}
        @return:
        @rtype:
        '''
        self.repository = repo
        self.auth_service = auth_service

    def post_message(self, chatroom, msg):
        m = self.factory.create_message(msg)
        return self.repository.save(m, chatroom)

    def get_messages(self, chatroom, from_time=None, to_time=None):
        return self.repository.get_messages(chatroom, from_time, to_time)


    def get_udid_token(self, udid):
        return self.auth_service.get_udid_token(udid)

    def authenticate(self, token):
        return self.auth_service.authenticate(token)


    # Don't think too hard about next two methods: it's shit and created for
    #  speed.
    def get_phone_for_person(self, person_id):
        query = """
            SELECT data_value
            FROM PERSON_DATA
            WHERE
                data_type='phone' AND
                id in (select id from person where person_id=%s)
            """
        def result(rows):
            res = []
            if rows:
                for row in rows:
                    res.append(row[0])
            return json.dumps(res)

        d = self.repository.pool.runQuery(query, (person_id,))
        d.addCallback(result)
        return d

    def get_person_by_phone(self, phone):
        query = """
            SELECT p.person_id
            FROM
                person p,
                person_data pd
            WHERE
                pd.data_value=%s AND
                pd.data_type='phone' AND
                pd.id = p.id
            """
        def result(row):
            if row:
                return row[0][0]
            else:
                return ''

        d = self.repository.pool.runQuery(query, (phone,))
        d.addCallback(result)
        return d
