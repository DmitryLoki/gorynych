__author__ = 'Boris Tsema'
import time

from gorynych.common.infrastructure import persistence as pe
from gorynych.chat.domain.model import MessageFactory


class MessageRepository(object):
    def __init__(self, pool):
        self.pool = pool

    def save(self, msg, chatroom_name):
        '''

        @param msg: message
        @type msg: L{gorynych.chat.domain.model.Message}
        @return: message id
        @rtype: C{int}
        '''
        d = self.pool.runQuery(pe.insert('message', 'chat'),
            (msg.from_, msg.sender, msg.to, msg.body, msg.timestamp,
            chatroom_name))
        d.addCallback(lambda x: str(x[0][0]))
        return d

    def get_messages(self, chatroom, start_time=None, end_time=None):
        '''
        Return messaged for specific chatroom for specific time.
        @param chatroom:
        @type chatroom:
        @param start_time:
        @type start_time:
        @param end_time:
        @type end_time:
        @return: list with readed messages.
        @rtype: C{list}
        '''
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = int(time.time())

        d = self.pool.runQuery(pe.select('message', 'chat'),
            (chatroom, start_time, end_time))
        d.addCallback(self._restore_messages)
        return d

    def _restore_messages(self, msglist):
        factory = MessageFactory()
        result = []
        if not msglist:
            return result
        for msg in msglist:
            m = dict(id=msg[0], from_=msg[1], sender=msg[2], to=msg[3],
                body=self._read_body(msg[4]), timestamp=msg[5])
            result.append(factory.create_message(m))
        return result

    def _read_body(self, msg):
        return str(msg)
        # return bytes(msg).decode('utf8')
