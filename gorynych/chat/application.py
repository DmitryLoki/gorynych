import json
import datetime

__author__ = 'Boris Tsema'

from zope.interface import Interface, implementer
from twisted.application.service import Service
from gorynych.common.domain.services import APIAccessor
from gorynych.chat.domain.model import MessageFactory
from gorynych.chat.domain.services import PrettyReportLog
from twisted.internet import defer

api = APIAccessor()


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

    def get_contest_id_for_retrieve_id(self, retrieve_id):
        '''
        Return contest id for retrieve_id
        @param retrieve_id:
        @type retrieve_id:
        @return:
        @rtype:
        '''
        return self.auth_service.get_contest_id_for_retrieve_id(retrieve_id)

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

    def get_chatroom_list(self):

        def nameficate(race_ids):
            result = []
            for race_id in race_ids:
                info = api.get_race_task(race_id)
                result.append((race_id, info['race_title'].encode('utf-8')))
            return result

        query = """
            SELECT chatroom_name
            FROM
                chatrooms
            """
        d = self.repository.pool.runQuery(query)
        d.addCallback(lambda rows: [item[0] for item in rows])
        d.addCallback(nameficate)
        return d

    def get_log(self, chatroom_id):

        def nameficate(log):
            for person_id in log:
                person_info = api.get_person(person_id)
                if not person_info:
                    continue
                log[person_id]['name'] = person_info['name']
            return log

        raw_log = api.get_chatroom(chatroom_id)
        logger = PrettyReportLog(raw_log)
        d = defer.Deferred()
        d.addCallback(lambda _: logger.format())
        d.addCallback(nameficate)
        d.callback('fire!')
        return d
