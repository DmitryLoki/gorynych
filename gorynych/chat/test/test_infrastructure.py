# coding=utf-8
import time

from twisted.trial import unittest
from twisted.internet import defer

from gorynych.chat import infrastructure
from gorynych.chat.domain import model
from gorynych.info.infrastructure.test.db_helpers import POOL
from gorynych.common.infrastructure import persistence as pe


class TestRepository(unittest.TestCase):
    def setUp(self):
        d = POOL.runOperation("delete from messages where chatroom_id=("
                              "select id from chatrooms where "
                              "chatroom_name='a')")
        d.addCallback(lambda _ :POOL.runOperation("delete from chatrooms where chatroom_name='a'"))
        d.addCallback(lambda _: POOL.runOperation("Insert into chatrooms ("
                                       "chatroom_name) values('a')"))
        return d

    @defer.inlineCallbacks
    def test_save(self):
        repo = infrastructure.MessageRepository(POOL)
        ts = int(time.time())
        m = model.Message(to='to', from_='from', body='body', timestamp=ts,
            sender='sender')
        res = yield repo.save(m, 'a')
        self.assertIsInstance(res, str)
        result = yield POOL.runQuery(pe.select('message', 'chat'), ('a', ts,
            ts))
        self.assertTupleEqual(result[0], (long(res), 'from', 'sender', 'to',
                            buffer('body'), ts))
        defer.returnValue('')


    @defer.inlineCallbacks
    def test_get(self):
        repo = infrastructure.MessageRepository(POOL)
        ts = int(time.time())
        m_id = yield POOL.runQuery(pe.insert('message', 'chat'),
            ('from', 'sender', 'to', bytes('body'), ts, 'a'))
        m_id = m_id[0][0]
        m = yield repo.get_messages('a', ts)
        self.assertIsInstance(m, list)
        m = m[0]
        self.assertTupleEqual((m.id, m.to, m.from_, m.sender, m.body,
        m.timestamp),
            (m_id, 'to', 'from', 'sender', 'body', ts))
