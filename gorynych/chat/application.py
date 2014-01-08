import json

__author__ = 'Boris Tsema'

from zope.interface import Interface, implementer
from gorynych.common.application import EventPollingService

from gorynych.chat.domain.model import MessageFactory

CREATE_CHATROOM = """
    INSERT INTO
        chatrooms(chatroom_name)
    VALUES(%s)
    """

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
class ChatApplication(EventPollingService):
    factory = MessageFactory()

    def __init__(self, pool, event_store, repo, auth_service):
        '''
        @param repo:
        @type repo:
        @param auth_service:
        @type auth_service: C{gorynych.chat.domain.services
        .AuthenticationService}
        @return:
        @rtype:
        '''
        EventPollingService.__init__(self, pool, event_store)
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

    def create_chatroom(self, chatroom):
        '''
        Create new chatroom with name chatroom.
        @param chatroom: Name of new chatroom.
        @type chatroom: str
        @return:
        @rtype: Deferred
        '''
        assert isinstance(chatroom, str), "Chatroom name must be str, " \
                                          "not %s." % type(chatroom)
        return self.repository.pool.runOperation(CREATE_CHATROOM, (chatroom,))

    def process_ContestRaceCreated(self, ev):
        chatroom_name = str(ev.payload)
        d = self.create_chatroom(chatroom_name)
        d.addCallback(lambda _:self.event_dispatched(ev.id))
        return d

    # Don't think too hard about next two methods: it's shit and created for
    #  speed.
    def get_phone_for_person(self, person_id):
        person_query = """
            SELECT data_value
            FROM PERSON_DATA
            WHERE
                data_type='phone' AND
                id in (select id from person where person_id=%s)
            """
        transport_query = """
            SELECT phone
            FROM TRANSPORT
            WHERE
                transport_id=%s
        """
        def result(rows):
            res = []
            if rows:
                for row in rows:
                    res.append(row[0])
            return json.dumps(res)

        if person_id[:4] == 'trns':
            query = transport_query
        else:
            query = person_query
        d = self.repository.pool.runQuery(query, (person_id,))
        d.addCallback(result)
        return d

    def get_person_by_phone(self, phone):
        person_query = """
            SELECT p.person_id
            FROM
                person p,
                person_data pd
            WHERE
                pd.data_value=%s AND
                pd.data_type='phone' AND
                pd.id = p.id
            """
        transport_query = """
            SELECT transport_id
            FROM
                transport
            WHERE
                phone=%s
            """

        def interaction(cur, phone):
            cur.execute(transport_query, (phone,))
            maybe_transport = cur.fetchone()
            if maybe_transport:
                return maybe_transport[0]
            cur.execute(person_query, (phone,))
            maybe_person = cur.fetchone()
            if maybe_person:
                return maybe_person[0]
            return ''

        d = self.repository.pool.runInteraction(interaction, phone)
        return d

