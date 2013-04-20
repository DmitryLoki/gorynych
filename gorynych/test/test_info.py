'''
Tests for info context.
'''
import json
import requests

import unittest
from gorynych.info.domain.test.test_race import create_checkpoints

URL = 'http://localhost:8085'

def create_contest():
    params = dict(title='Contest with paragliders', start_time=1,
        end_time=10,
        place = 'La France', country='ru',
        hq_coords='43.3,23.1', timezone='Europe/Paris')
    r = requests.post(URL + '/contest', data=params)
    return r.json()['id']


def create_persons():
    params = dict(name='Vasylyi', surname='Doe', country='SS',
        email='vasya@example.com', reg_date='2012,12,12')
    r = requests.post(URL + '/person', data=params)
    return r.json()['id']


def find_contest_with_paraglider():
        contest_list = requests.get(URL + '/contest')
        for cont in contest_list.json():
            r = requests.get('/'.join((URL, 'contest', cont['id'],
                'paraglider')))
            paragliders_list = r.json()
            if paragliders_list:
                return cont['id'], paragliders_list[0]['person_id']


def register_paraglider(pers_id, cont_id):
    params = dict(person_id=pers_id, glider='gArlem 88',
                  contest_number='666')
    r = requests.post('/'.join((URL, 'contest', cont_id,
                                'paraglider')), data=params)
    if not r.status_code == 201:
        raise Exception
    return r



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
            hq_coords='43.3,23.1', timezone='Europe/Moscow')
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
            coords='42.3,11.3', timezone='Europe/Paris'))
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

    def test_1_register_paragliders(self):
        try:
            cont_id = create_contest()
            pers_id = create_persons()
        except Exception:
            raise unittest.SkipTest("Contest and persons hasn't been created"
                                    ".")
        if not cont_id and not pers_id:
            self.skipTest("Can't test without contest and race.")
        r = register_paraglider(pers_id, cont_id)
        self.assertEqual(r.status_code, 201)
        result = r.json()
        self.assertEqual(result['person_id'], pers_id)
        self.assertEqual(result['glider'], 'garlem')
        self.assertEqual(result['contest_number'], '666')

        # test get paragliders. it's supposed to be in separate testcase,
        # but I'm lazy to know how to store this cont_id.
        r2 = requests.get('/'.join((self.url, 'contest', cont_id,
                                    'paraglider')))
        self.assertEqual(r2.status_code, 200)
        result2 = r2.json()[0]
        self.assertTrue(result2.has_key('glider'))
        self.assertTrue(result2.has_key('contest_number'))
        self.assertTrue(result2.has_key('person_id'))

    def test_2_change_paraglider(self):
        results = find_contest_with_paraglider()
        if not results or (None in results):
            raise unittest.SkipTest("Can't test without contest and "
                                    "paraglider.")
        cont_id, p_id = results
        params = json.dumps(dict(glider='marlboro', contest_number='13'))
        r = requests.put('/'.join((self.url, 'contest', cont_id,
                                   'paraglider', p_id)), data=params)
        self.assertEqual(r.status_code, 200)
        result = r.json()
        self.assertEqual(result['contest_number'], '13')
        self.assertEqual(result['glider'], 'marlboro')


class ContestRaceTest(unittest.TestCase):
    def test_create_and_read_race(self):
        try:
            c_id = create_contest()
            p_id = create_persons()
            i = register_paraglider(p_id, c_id)
        except:
            raise unittest.SkipTest("I need contest and paraglider for test")
        if not (p_id and c_id):
            raise unittest.SkipTest("I need contest and paraglider for test")

        ch_list = create_checkpoints()
        for i, item in enumerate(ch_list):
            ch_list[i] = item.__geo_interface__
        params = dict(title="Task 8", race_type='opendistance', bearing=12,
                      checkpoints=json.dumps(ch_list))
        r = requests.post('/'.join((URL, 'contest', c_id, 'race')),
                         data=params)
        race_id = r.json()['id']
        self.assertEqual(r.status_code, 201)
        self.assertDictContainsSubset({'type':'opendistance',
                                       'title':'Task 8', 'start_time': '2',
                                       'end_time': '8'}, r.json())

        # Assume that races has been successfully created.
        r = requests.get('/'.join((URL, 'contest', c_id, 'race')))
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)
        self.assertDictContainsSubset({'type':'opendistance',
                                       'title':'Task 8', 'start_time': '2',
                                       'end_time': '8'}, r.json()[0])

        r = requests.get('/'.join((URL, 'contest', c_id, 'race', race_id)))
        result = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(result['checkpoints']['features'],
                         json.loads(json.dumps(ch_list)))
        self.assertEqual(result['race_title'], 'Task 8')
        self.assertEqual(result['timezone'], 'Europe/Paris')


if __name__ == '__main__':
    unittest.main()
