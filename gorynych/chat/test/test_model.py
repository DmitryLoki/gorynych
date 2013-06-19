# coding=utf-8
import unittest
import time

from gorynych.chat.domain import model


class TestMessageFactory(unittest.TestCase):
    def test_create_message(self):
        ts = int(time.time())
        m = dict(timestamp=ts, body='здравствуйте', sender='sender', to='to')
        m['from'] = 'from'

        res = model.MessageFactory().create_message(m)
        self.assertEqual(res.body, u'здравствуйте')


if __name__ == '__main__':
    unittest.main()
