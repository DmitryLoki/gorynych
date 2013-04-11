'''
Tests for info context.
'''
import json
import requests

import unittest




class RESTAPITest(unittest.TestCase):
    '''
    REST API must be started and running before tests.
    '''
    url = 'http://localhost:8085'

    def test_main_page(self):
        r = requests.get(self.url)
        self.assertEqual(r.status_code, 404)



class ContestRESTAPITest(unittest.TestCase):
    url = 'http://localhost:8085/contest/'
    def test_1_get_no_contests(self):
        '''
        Here I suppose that contest repository is empty.
        '''
        self.skipTest("I'm lazy and don't want to clean repository.")
        r = requests.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {})

    def test_1_get_fake_contest(self):
        '''
        Here I suppose that there is no resource with such id.
        '''
        r = requests.get(self.url+'/1-1-1-1')
        self.assertEqual(r.status_code, 404)

    def test_2_create_contest(self):
        params = dict(title='Best contest', start_time=1, end_time=10,
            place = 'La France', country='ru',
            hq_coords='43.3,23.1')
        r = requests.post(self.url, data=params)
        self.assertEqual(r.status_code, 201)
        result = r.json()
        self.assertEqual(result['title'], u'Best Contest')
        self.cont_id = result['id']
        r2 = requests.get('/'.join((self.url, result['id'])))
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['title'], 'Best Contest')

    def test_3_change_contest(self):
        r = requests.get(self.url)
        cont_id = r.json()[0]["id"]
        params = json.dumps(dict(title='besT Contest changed  ',
            start_time=11, end_time=15, place='Paris', country='mc',
            coords='42.3,11.3'))
        r2 = requests.put(self.url + cont_id, data=params)
        result = r2.json()
        self.assertEqual(result['title'], 'Best Contest Changed')
        self.assertEqual(result['country'], 'MC')


class PersonAPITest(unittest.TestCase):
    url = 'http://localhost:8085/person/'
    def test_1_get_no_persons(self):
        self.skipTest("I'm lazy and don't want to clean repository.")
        r = requests.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {})

    def test_1_get_fake_person(self):
        r = requests.get(self.url+'/1-1-1-1')
        self.assertEqual(r.status_code, 404)

    def test_2_create_person(self):
        params = dict(name='Vasylyi', surname='Doe', country='SS',
            email='vasya@example.com', reg_date='2012,12,12')
        r = requests.post(self.url, data=params)
        result = r.json()
        self.assertEqual(r.status_code, 201)
        r2 = requests.get(self.url+result['id'])
        self.assertEqual(r2.json()['id'], result['id'])

    def test_3_get_person(self):
        r = requests.get(self.url)
        p_id = r.json()[0]['id']
        r2 = requests.get(self.url + p_id)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['id'], p_id)

    def test_3_change_person(self):
        r = requests.get(self.url)
        p_id = r.json()[0]['id']
        params = json.dumps(dict(name="Juan", surname="CarlOs",
            country="MEXICO!"))
        r2 = requests.put(self.url + p_id, data=params)
        self.assertEqual(r2.status_code, 200)
        result = r2.json()
        self.assertEqual(result['name'], 'Juan Carlos')
        self.assertEqual(result['country'], 'ME')


class ParaglidersTest(unittest.TestCase):
    url = 'http://localhost:8085'
    def _create_contest(self):
        params = dict(title='Contest with paragliders', start_time=1,
            end_time=10,
            place = 'La France', country='ru',
            hq_coords='43.3,23.1')
        r = requests.post(self.url + '/contest', data=params)
        return r.json()['id']

    def _create_persons(self):
        params = dict(name='Vasylyi', surname='Doe', country='SS',
            email='vasya@example.com', reg_date='2012,12,12')
        r = requests.post(self.url + '/person', data=params)
        result = r.json()
        return result['id']

    def test_register_paragliders(self):
        try:
            cont_id = self._create_contest()
            pers_id = self._create_persons()
        except Exception:
            raise unittest.SkipTest("Contest and persons hasn't been created"
                                    ".")
        if not cont_id and not pers_id:
            self.skipTest("Can't test without contest and race.")
        params = dict(person_id=pers_id, glider='gArlem 88',
            contest_number='666')
        r = requests.post('/'.join((self.url, 'contest', cont_id,
                                    'paraglider')), data=params)
        print r.text
        self.assertEqual(r.status_code, 201)
        result = r.json()
        self.assertEqual(result['person_id'], pers_id)
        self.assertEqual(result['glider'], 'garlem')
        self.assertEqual(result['contest_number'], '666')



if __name__ == '__main__':
    unittest.main()
