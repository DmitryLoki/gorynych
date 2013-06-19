# coding=utf-8
import unittest

import requests

URL = 'http://localhost:8085'

class TestChatResource(unittest.TestCase):
    def test_post_get_message(self):
        params = dict(to='you', body=u'hello, землянин', sender='its_test')
        params['from'] = 'me'
        r = requests.post(URL + '/chatroom/a', data=params)
        self.assertEqual(r.status_code, 201)
        msg_id = int(r.text)

        # test GET message
        r = requests.get(URL + '/chatroom/a')
        self.assertEqual(r.status_code, 200)
        res = r.json()
        for r in res:
            if r['sender'] == 'its_test':
                break
        self.assertDictContainsSubset(
            {'from':'me', 'sender':'its_test', 'to':'you',
                'body':u'hello, землянин'},r)


if __name__ == '__main__':
    unittest.main()
