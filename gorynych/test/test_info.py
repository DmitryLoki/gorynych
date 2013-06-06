'''
Tests for info context.
'''
import json
import time

import requests
import unittest

from gorynych.info.domain.test.helpers import create_checkpoints

URL = 'http://localhost:8085'

def create_contest(title='Contest with paragliders'):
    params = dict(title=title, start_time=1,
        end_time=10,
        place = 'La France', country='ru',
        hq_coords='43.3,23.1', timezone='Europe/Paris')
    r = requests.post(URL + '/contest', data=params)
    if not r.status_code == 201:
        print r.text
    return r.json()['id']


def create_persons():
    params = dict(name='Vasylyi', surname='Doe', country='SS',
        email='vasya@example.com', reg_date='2012,12,12')
    r = requests.post(URL + '/person', data=params)
    return r.json()['id']


def create_geojson_checkpoints(ch_list=None):
    if not ch_list:
        ch_list = create_checkpoints()
    for i, item in enumerate(ch_list):
        ch_list[i] = item.__geo_interface__
    return json.dumps(dict(type='FeatureCollection',
                                  features=ch_list))


def create_race(contest_id, checkpoints=None, race_type='racetogoal',
                bearing=None):
    if not checkpoints:
        checkpoints = create_geojson_checkpoints()
    params = dict(title="Task 8", race_type=race_type,
                   checkpoints=checkpoints)
    if bearing:
        params['bearing'] = bearing
    return requests.post('/'.join((URL, 'contest', contest_id, 'race')),
                     data=params)

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

    def test_main_page(self):
        r = requests.get(URL)
        self.assertEqual(r.status_code, 404)


class ContestRESTAPITest(unittest.TestCase):
    url = URL + '/contest'
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
        params = dict(title='Best contest', start_time='1', end_time='10',
            place = 'La France', country='ru',
            hq_coords='43.3,23.1', timezone='Europe/Moscow')
        r = requests.post('/'.join((URL, 'contest')), data=params)
        self.assertEqual(r.status_code, 201)
        result = r.json()
        self.assertEqual(result['title'], u'Best Contest')
        r2 = requests.get('/'.join((self.url, result['id'])))
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['title'], 'Best Contest')

    def test_3_change_contest(self):
        try:
            r = requests.get('/'.join((URL, 'contest')))
            cont_id = r.json()[0]["id"]
        except:
            raise unittest.SkipTest("Can't get contest id is needed for this "
                                 "test.")
        params = json.dumps(dict(title='besT Contest changed  ',
            start_time=11, end_time=15, place='Paris', country='mc',
            coords='42.3,11.3', timezone='Europe/Paris'))
        r2 = requests.put('/'.join((URL, 'contest', cont_id)), data=params)
        result = r2.json()
        self.assertEqual(result['title'], 'Best Contest Changed')
        self.assertEqual(result['country'], 'MC')


class PersonAPITest(unittest.TestCase):
    url = URL + '/person/'
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
        time.sleep(1)
        result = r.json()
        self.assertEqual(r.status_code, 201)
        link = self.url + result['id']
        r2 = requests.get(link)
        self.assertEqual(r2.status_code, 200)
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
        r2 = requests.get('/'.join((URL, 'contest', cont_id,
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
        r = requests.put('/'.join((URL, 'contest', cont_id,
                                   'paraglider', p_id)), data=params)
        self.assertEqual(r.status_code, 200)
        result = r.json()
        self.assertEqual(result['contest_number'], '13')
        self.assertEqual(result['glider'], 'marlboro')


class ContestRaceTest(unittest.TestCase):
    def setUp(self):
        try:
            c_id = create_contest(title='Contest with checkpoints and race')
            p_id = create_persons()
            i = register_paraglider(p_id, c_id)
        except:
            raise unittest.SkipTest("I need contest and paraglider for test")
        if not (p_id and c_id):
            raise unittest.SkipTest("I need contest and paraglider for test")
        self.c_id = c_id
        self.p_id = p_id

    def test_1_create_race(self):
        chs = create_geojson_checkpoints()
        r = create_race(self.c_id, chs, race_type='opendistance', bearing=12)
        self.assertEqual(r.status_code, 201)
        # race_id = r.json()['id']
        self.assertDictContainsSubset({'type':'opendistance',
                                       'title':'Task 8',
                                       'start_time': '1347711300',
                                       'end_time': '1347732000'
                                       }, r.json())

    def test_2_get_race(self):
        # Test GET /contest/{id}/race
        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race')))
        print r.text
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)
        self.assertDictContainsSubset({'type':'opendistance',
                                       'title':'Task 8',
                                       'start_time': '1347711300',
                                       'end_time': '1347732000'}, r.json()[0])

    def test_3_get_concrete_race(self):
        time.sleep(2)
        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race')))
        print r.text
        race_id = r.json()['id']
        print race_id
        # Test GET /contest/{id}/race/{id}
        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race', race_id)))
        chs = create_geojson_checkpoints()
        result = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(result['bearing'], '12')
        self.assertEqual(result['checkpoints'], json.loads(chs))
        self.assertEqual(result['race_title'], 'Task 8')
        self.assertEqual(result['timezone'], 'Europe/Paris')

        # Test PUT /contest/{id}/race/{id}
        new_ch_list = create_checkpoints()
        new_ch_list[0].name = 'HAHA'
        for i, item in enumerate(new_ch_list):
            new_ch_list[i] = item.__geo_interface__
        params = dict(race_title='Changed race', bearing=8, checkpoints=json
            .dumps({'type': 'FeatureCollection', 'features': new_ch_list}))
        r = requests.put('/'.join((URL, 'contest', self.c_id, 'race', race_id)),
                         data=json.dumps(params))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['race_title'], 'Changed Race')
        self.assertEqual(r.json()['bearing'], '8')
        self.assertEqual(r.json()['checkpoints']['features'],
                         json.loads(json.dumps(new_ch_list)))

        # Test POST /contest/{id}/race/{id}/track_archive
        r = requests.post('/'.join((URL, 'contest', self.c_id, 'race', race_id,
                   'track_archive')), data={'url':'http://airtribune.com/1'})
        self.assertEqual(r.json()['status'],
            "Archive with url http://airtribune.com/1 added.")

    def test_get_race_paragliders(self):
        try:
            c_id = create_contest(title='Contest with checkpoints and race')
            p_id = create_persons()
            i = register_paraglider(p_id, c_id)
            ch_list = create_checkpoints()
            race_id = create_race(c_id).json()['id']
        except Exception as error:
            raise unittest.SkipTest("Something went wrong and I need race "
                                    "for test: %r" % error)
        if not (p_id and c_id and race_id):
            raise unittest.SkipTest("I need race for test")

        r = requests.get('/'.join((URL, 'contest', c_id, 'race', race_id)))
        self.assertEqual(r.status_code, 200)
        r = requests.get('/'.join((URL, 'contest', c_id, 'race', race_id,
                                    'paraglider')))
        self.assertEqual(r.status_code, 200)
        self.assertDictContainsSubset({'glider':'garlem',
                                       'contest_number':'666',
                                       'name':'V. Doe', 'country':'SS'},
                                      r.json()[0])


if __name__ == '__main__':
    unittest.main()
