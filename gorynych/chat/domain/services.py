import time
import datetime

from twisted.internet import defer
from twisted.python import log

from gorynych.common.infrastructure import persistence as pe
from gorynych.common.exceptions import AuthenticationError
from gorynych.common.domain.services import AsynchronousAPIAccessor
from gorynych.info.domain.ids import namespace_date_random_validator

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
        time_offset = 3600 * 9
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
            if int(item['start_time']) < now < int(item['end_time']) + time_offset:
                result = item
                break
        if result:
            defer.returnValue(result['id'])
        else:
            raise AuthenticationError()


class OldMessageParser(object):
    FORMAT = {
        'OUT': '',
        'IN': 'organization'
    }

    def parse(self, message):
        if message['sender'] == self.FORMAT['IN']:
            person_id = message['from']
            message['direction'] = 'IN'
        elif message['sender'] == self.FORMAT['OUT']:
            person_id = message['to']
            message['direction'] = 'OUT'
        else:
            person_id, message = (None, None)
        return person_id, message


class NewMessageParser(object):
    FORMAT = {
        'IN': 'SMS retriever',
        'OUT': 'web_app'
    }

    def parse(self, message):
        inlen = len(self.FORMAT['IN'])
        outlen = len(self.FORMAT['OUT'])
        if message['sender'][:inlen] == self.FORMAT['IN']:
            person_id = message['from']
            message['direction'] = 'IN'
        elif message['sender'][:outlen] == self.FORMAT['OUT']:
            person_id == message['to']
            message['direction'] = 'OUT'
        else:
            person_id, message = (None, None)
        return person_id, message


class ParsingDispatcher(object):

    def parse(self, message):
        parser = OldMessageParser if message['sender'] in OldMessageParser.FORMAT.values()\
            else NewMessageParser
        return parser().parse(message)


class PrettyReportLog(object):
    # contstants
    RESPONSE_DELAYED = 5 * 60
    COMMENTS = {
        'delayed': 'Long response detected!',
        'failed': 'No answer detected!',
        'nothing': ''
    }

    def _prepare(self, log):
        """
        Runs across the log, extracts persons, defines direction
        and all the other stuff.
        """
        metaparser = ParsingDispatcher()

        persons = set()
        prepared_log = []

        for message in log:
            person_id, message = metaparser.parse(message)
            if person_id and message:
                persons.add(person_id)
                prepared_log.append(message)

        return persons, prepared_log

    def __init__(self, log):
        self.OLD_STATUS = 'Fly'
        self.persons, self.body = self._prepare(log)

    def format(self):
        formatted = {}
        for person_id in self.persons:
            personal_log = [message for message in self.body if message['from'] == person_id
                            or message['to'] == person_id]

            formatted[person_id] = {
                'messages': [],
                'sms_count': len(personal_log)
            }

            for i, message in enumerate(personal_log):
                if message['direction'] == 'IN':
                    comment_type = self._get_response(
                        message, personal_log[i:])
                    timelapse = None
                else:
                    comment_type, timelapse = self._get_request(
                        message, personal_log[:i])
                formatted[person_id]['messages'].append(self._format_message(
                    message, comment_type, timelapse))

        return formatted

    def _format_message(self, message, comment_type, timelapse=None):
        formatted = {
            'comment_type': comment_type,
            'comment': self.COMMENTS[comment_type],
            'direction': message['direction']
        }
        if message['body'][:6] == 'system':
            formatted['body'] = self._get_system_body(message['body'])
        else:
            formatted['body'] = message['body']

        if message['direction'] == 'IN':
            formatted.update({
                'operator': '',
                'ts': datetime.datetime.fromtimestamp(message['timestamp']).strftime('%d.%m - %H:%M'),
            })
        else:
            formatted.update({
                'operator': message['from'],
                'ts': '{} ({})'.format(
                    datetime.datetime.fromtimestamp(message[
                                                    'timestamp']).strftime('%d.%m - %H:%M'),
                    timelapse),
            })
        return formatted

    def _get_system_body(self, body, old_status):
        bodyarr = body.split(':')
        if len(bodyarr) != 3:
            return 'UNKNOWN: {}'.format(body)
        if bodyarr[1] == 'new_status':
            new_status = bodyarr[2]
            self.OLD_STATUS = new_status
            return 'STATUS CHANGED: {} > {}'.format(old_status, new_status)
        else:
            # ...other nonexistent stuff
            pass
        return 'UNKNOWN: {}'.format(body)

    def _get_response(self, message, rest_log):
        print 'i am', message
        print 'thats ahead', rest_log
        if len(rest_log) < 2:
            return 'failed'
        if rest_log[1]['direction'] == 'OUT':
            # got response right now
            if rest_log[1]['timestamp'] - message['timestamp'] < self.RESPONSE_DELAYED:
                return 'nothing'
            else:
                return 'delayed'
        else:
            # looping
            for i, next in enumerate(rest_log[1:]):
                if next['direction'] == 'IN' and\
                        next['timestamp'] - message['timestamp'] < self.RESPONSE_DELAYED:
                    return self._get_response(next, rest_log[1 + i:])
            # no response right now
            return 'failed'

    def _get_request(self, message, prev_log):
        if not prev_log:
            timelapse = 0
        elif prev_log[0]['direction'] == 'OUT':
            # another response before. we've already processed it
            timelapse = 0
        else:
            for i, request in enumerate(prev_log):
                if i != len(prev_log) - 1:
                    if prev_log[i + 1]['direction'] == 'in' and\
                            message['timestamp'] - prev_log[i + 1]['timestamp'] > self.RESPONSE_DELAYED:
                        continue
                timelapse = message['timestamp'] - prev_log[i]['timestamp']

        # stringification
        comment_type = 'delayed' if timelapse > self.RESPONSE_DELAYED else 'nothing'
        if timelapse > 60:
            timelapse_str = '{}m {}s'.format(
                timelapse / 60, timelapse % 60)
        else:
            timelapse_str = '{}s'.format(timelapse)
        return comment_type, timelapse_str
