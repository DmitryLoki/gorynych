import json
import datetime

__author__ = 'Boris Tsema'

from zope.interface import Interface, implementer
from twisted.application.service import Service
from gorynych.common.domain.services import APIAccessor
from gorynych.chat.domain.model import MessageFactory
from gorynych.info.domain.ids import namespace_date_random_validator
from jinja2 import Environment, PackageLoader
from twisted.internet import defer

env = Environment(loader=PackageLoader('gorynych', 'templates'))


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
        print 'here da fuck'
        api = APIAccessor()

        def get_race_task(race_id):
            return api.get_race_task(race_id)

        def nameficate(race_ids):
            result = []
            for race_id in race_ids:
                info = get_race_task(race_id)
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

        template = env.get_template('chatroom_list.html')
        d.addCallback(lambda x: template.render(
            api_url=api.url, data=x).encode('utf-8'))

        return d

    def get_log(self, chatroom_id):
        # contstants
        RESPONSE_DELAYED = 5 * 60
        OLD_STATUS = 'Fly'
        COMMENTS = {
            'delayed': 'Long response detected!',
            'failed': 'No answer detected!',
            'nothing': ''
        }

        api = APIAccessor()

        def get_chatroom(chatroom_id):
            return api.get_chatroom(chatroom_id)

        log = api.get_chatroom(chatroom_id)
        persons = set()
        for message in log:
            if message['to'] == 'SYSTEM':
                continue
            try:
                print 'from', message['from']
                namespace_date_random_validator(message['from'], 'pers')
                persons.add(message['from'])
                message['direction'] = 'in'
            except (AssertionError, ValueError) as e:
                try:
                    print 'to', message['to']
                    namespace_date_random_validator(message['to'], 'pers')
                    persons.add(message['to'])
                    message['direction'] = 'out'
                except (AssertionError, ValueError) as e:
                    continue

        def try_get_response(message, rest_log):
            if not rest_log:
                return 'failed'
            if rest_log[0]['direction'] == 'out':
                # got response right now
                if rest_log[0]['timestamp'] - message['timestamp'] < RESPONSE_DELAYED:
                    return 'nothing'
                else:
                    return 'delayed'
            else:
                # no response right now
                return 'failed'

        def try_get_request(message, prev_log):
            if not prev_log:
                return 0
            if prev_log[0]['direction'] == 'out':
                # another response before. we've already processed it
                return 0
            for i, request in enumerate(prev_log):
                if i != len(prev_log) - 1:
                    if prev_log[i + 1]['direction'] == 'in' and\
                            message['timestamp'] - prev_log[i + 1]['timestamp'] > RESPONSE_DELAYED:
                        continue
                return message['timestamp'] - prev_log[i]['timestamp']

        def get_system_body(body, old_status):
            bodyarr = body.split(':')
            if len(bodyarr) != 3:
                return 'UNKNOWN: {}'.format(body)
            if bodyarr[1] == 'new_status':
                new_status = bodyarr[2]
                global OLD_STATUS
                OLD_STATUS = new_status
                return 'STATUS CHANGED: {} > {}'.format(old_status, new_status)
            else:
                # ...other nonexistent stuff
                pass
            return 'UNKNOWN: {}'.format(body)

        formatted = {}
        print 'my persons!'
        print list(persons)
        for person in list(persons):
            print person
            personal_log = [x for x in log if x['to'] == person
                            or x['from'] == person]
            person_info = api.get_person(person)
            formatted[person] = {
                'name': person_info['name'],
                'sms_count': len(personal_log),
                'messages': personal_log
            }

            for i, message in enumerate(personal_log):

                if message.get('direction') == 'in':
                    comment_type = try_get_response(message, personal_log[i:])
                    formatted[person]['messages'].append({
                        'type': 'in',
                        'body': message['body'],
                        'operator': '',
                        'ts': message['timestamp'],
                        'comment_type': comment_type,
                        'comment': COMMENTS[comment_type]
                    })

                elif message.get('direction') == 'out':
                    timelapse = try_get_request(message, personal_log[:i])
                    comment_type = 'delayed' if timelapse > RESPONSE_DELAYED else 'nothing'
                    if timelapse > 60:
                        timelapse_str = '{}m {}s'.format(
                            timelapse / 60, timelapse % 60)
                    else:
                        timelapse_str = '{}s'.format(timelapse)
                    formatted[person]['messages'].append({
                        'type': 'out',
                        'body': message['body'],
                        'operator': message['from'],
                        'ts': '{} ({})'.format(datetime.datetime.fromtimestamp(message['timestamp']).strftime('%d.%m - %H:%M'),
                                               timelapse_str),
                        'comment_type': comment_type,
                        'comment': COMMENTS[comment_type]
                    })

                elif message.get('to') == 'SYSTEM':
                    formatted[person]['messages'].append({
                        'type': 'system',
                        'ts': datetime.datetime.fromtimestamp(message['timestamp']).strftime('%d.%m - %H:%M'),
                        'operator': message['from'],
                        'body': get_system_body(message['body'], OLD_STATUS),
                        'comment': ''
                    })
        print formatted
        template = env.get_template('chat_log.html')
        d = defer.Deferred()

        d.addCallback(lambda _: template.render(
            data=formatted).encode('utf-8'))
        return d
