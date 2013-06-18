from datetime import date
import time

__author__ = 'Boris Tsema'
from gorynych.common.domain.model import ValueObject

class Message(ValueObject):
    def __init__(self, **kw):
        self.timestamp = kw['timestamp']
        self.body = kw['body']
        self.sender = kw['sender']
        self.from_ = kw.get('from_') or kw.get('from')
        self.to = kw['to']
        self.id = kw.get('id')


class MessageFactory(object):
    earliest_possible_message = date(2013, 6, 17)

    def create_message(self, msg):
        '''
        Create C{Message} from incoming dictionary.
        @param msg: {body, sender, from_, to, id, timestamp}
        @type msg: C{dict}
        @return:
        @rtype: C{Message}
        '''
        if not msg.get('timestamp'):
            ts = int(time.time())
        else:
            ts = self._check_message_timestamp(msg['timestamp'])
        body = msg['body']
        msg['from'] = msg.get('from') or msg.get('from_')
        return Message(timestamp=ts, body=body, sender = msg['sender'],
            from_=msg['from'], to=msg['to'], id=msg.get('id'))

    def _check_message_timestamp(self, ts):
        assert isinstance(ts, int), "Timestamp should be integer."
        assert self.earliest_possible_message < date.fromtimestamp(ts), \
            "Entered message time %s earlier then allowed June 17 2013." % ts
        assert ts < time.time() + 60, "I've got message from future!!!"
        return ts

