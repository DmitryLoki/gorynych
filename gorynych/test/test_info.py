'''
Tests for info context.
'''
import requests

import unittest




class RESTAPITest(unittest.TestCase):
    '''
    REST API must be started and running before tests.
    '''
    url = 'http://localhost:8080'
#    skip = 'Not ready yet.'

#    @classmethod
#    def setUp(self):
#        os.chdir('..')
#        filename = os.path.join(os.getcwd(), 'gorynych/info/info.tac')
#        subprocess.check_call('twistd -y ' + filename+ ' --logfile=info.log '
#                              '--pidfile=info.pid', shell=True)
#
#    @classmethod
#    def tearDown(self):
#        subprocess.check_call('kill `cat info.pid`', shell=True)


    def test_main_page(self):
        r = requests.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_1_create_person(self):
        self.skipTest("Not ready yet")
        params = {'name': 'Vasya', 'surname': 'Petrov', 'country': 'RU',
                  'email': 'vasya@example.com', 'reg_date': '2012,12,21'}
        r = requests.post(self.url+'/person', data=params)
        self.assertEqual(r.json()['name'], "Vasya Petrov")
        params = {'name': 'Vasya', 'surname': 'Petrov', 'country': 'RU',
                  'email': 'vasya@example.com'}
        r = requests.post(self.url+'/person', data=params)

    def test_2_get_persons(self):
        self.skipTest("Not ready today")
        r = requests.get(self.url+'/person')
        result = r.json()
        self.assertIsInstance(result, list)
        self.assertTrue(len(result)>0)
        vasyas = []
        for item in result:
            self.assertIsInstance(item, dict)



class ContestRESTAPITest(unittest.TestCase):
    url = 'http://localhost:8080/contest'
    def test_1_get_no_contests(self):
        '''
        Here I suppose that contest repository is empty.
        '''
        r = requests.get(self.url)
        self.assertEqual(r.json(), {})

    def test_1_get_empty_contest(self):
        '''
        Here I suppose that there is no resource with such id.
        '''
        r = requests.get(self.url+'/1-1-1-1')
        self.assertEqual(r.status_code, 404)

    def test_2_create_contest(self):
        self.skipTest("Not ready yet")
        params = dict(title='Best contest', start_time=1, end_time=10,
            contest_place = 'La France', contest_country='ru',
            hq_coords='43.3,23.1')
        r = requests.post(self.url, data=params)
        print r.text
        self.assertEqual(r.status_code, 201)
        result = r.json()
        self.assertEqual(result['title'], 'Best contest')
        cont_id = result['id']
        r2 = requests.get('/'.join((self.url, result['id'])))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['title'], 'Best contest')


if __name__ == '__main__':
    unittest.main()
