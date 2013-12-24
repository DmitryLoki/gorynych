# coding=utf-8
'''
Tests for info context.
'''
import json
import time
import random
import unittest

import requests
# from twisted.trial import unittest

from gorynych.info.domain.test.helpers import create_checkpoints

URL = 'http://localhost:8085'

def create_contest(title='Contest with paragliders'):
    title = title + '_' + str(random.randint(1, 1000000))
    params = dict(title=title, start_time=1,
        end_time=int(time.time()),
        place = 'La France', country='ru',
        hq_coords=[43.3, 23.1], timezone='Europe/Paris')
    r = requests.post(URL + '/contest', data=json.dumps(params), headers={'Content-Type': 'application/json'})
    if not r.status_code == 201:
        print r.text
    return r, title


def create_persons(reg_date=None, email=None, name=None, phone=None, udid=None):
    if not email:
        email = 'vasya@example.com'+ str(random.randint(1, 1000000))
    if not name:
        name='Vasylyi'
    params = dict(name=name, surname='Doe', country='SS',
        email=email, reg_date=reg_date)
    if phone:
        params.update({'phone': phone})
    if udid:
        params.update({'udid': udid})
    r = requests.post(URL + '/person', data=json.dumps(params), headers={'Content-Type': 'application/json'})
    return r, email


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
                     data=json.dumps(params), headers={'Content-Type': 'application/json'})

def find_contest_with_paraglider():
        contest_list = requests.get(URL + '/contest')
        for cont in contest_list.json():
            r = requests.get('/'.join((URL, 'contest', cont['id'],
                'paraglider')))
            paragliders_list = r.json()
            if paragliders_list:
                return cont['id'], paragliders_list[0]['person_id']


def register_paraglider(pers_id, cont_id):
    cn = random.randint(1, 10000)
    params = dict(person_id=pers_id, glider='gArlem 88',
                  contest_number=str(cn))
    r = requests.post('/'.join((URL, 'contest', cont_id,
                                'paraglider')), data=json.dumps(params),
                                 headers={'Content-Type': 'application/json'})
    if not r.status_code == 201:
        raise Exception
    return r, cn


def create_transport(ttype=None, title=None, description=None):
    if not ttype:
        ttype='bus'
    if not title:
        title='Some bus.'
    params = dict(type=ttype, title=title, description=description)
    r = requests.post(URL + '/transport', data=json.dumps(params), headers={'Content-Type': 'application/json'})
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
    def test_1_get_fake_contest(self):
        '''
        Here I suppose that there is no resource with such id.
        '''
        r = requests.get(self.url+'/1-1-1-1')
        self.assertEqual(r.status_code, 404)

    def test_2_create_contest(self):
        result, title = create_contest(u'Best conteâst')
        self.assertEqual(result.status_code, 201)
        result = result.json()
        self.assertEqual(result['title'], title)
        r2 = requests.get('/'.join((self.url, result['id'])))
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['title'], title)

    def test_3_change_contest(self):
        try:
            c_, t_ = create_contest()
            cont_id = c_.json()["id"]
        except:
            raise unittest.SkipTest(
                "Can't get contest id which is needed for this test.")
        title = '  besT Contest changed' + str(random.randint(1, 1000)) + '  '
        params = json.dumps(dict(title=title,
            start_time=11, end_time=15, place='Paris', country='mc',
            coords='42.6,11.3', timezone='Europe/Paris', retrieve_id='45'))
        r2 = requests.put('/'.join((self.url, cont_id)), data=params)
        result = r2.json()
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(result['title'], title.strip())
        self.assertEqual(result['country'], 'MC')
        self.assertEqual(result['coords'], [42.6, 11.3])
        self.assertEqual(result['retrieve_id'], '45')

        params = json.dumps(dict(retrieve_id='some retrieve'))
        r3 = requests.put('/'.join((self.url, cont_id)), data=params)
        self.assertEqual(r3.status_code, 200)
        result = r3.json()
        self.assertEqual(result['title'], title.strip())
        self.assertEqual(result['country'], 'MC')
        self.assertEqual(result['coords'], [42.6, 11.3])
        self.assertEqual(result['retrieve_id'], 'some retrieve')


class ValidatedTestCase(unittest.TestCase):
    """
    Allows response validation. Call self.validate with
    response and format arguments, where format is a key-type dictionary
    like that:

    format = {
        "id": int,
        "name": str,
        "list_attribute": (list, int),
        "dict_attribute": {
            "lat": float,
            "lng": float
        }
    }

    It follows these simple rules:
        1) All format's keys must be presented in the response.
        2) If a validated key is a single value, you should supply format with its type (like int)
        3) If a validated key is a multi-valued container, like a list, tuple or set,
           specify a tuple (list, <type>), where <type> is a type of container element.
           (list, int) is a correct format for [1, 2, 3].
        4) Dealing with heterogeouns container (list containing values of different types),
           specify format as a list of types (example: (list, [int, float, int]) for [1, 0.4, 2])
        5) If a validated key is a dictionary, treat it like another 'response' and specify
           a sub-dictionary format.
    """
    def validate(self, response, format):
        # enforce unicode
        if format == str:
            format = unicode

        if isinstance(format, dict):
            self.assertIsInstance(response, dict)
            for key, value in format.iteritems():
                self.assertIn(key, response)
                self.validate(response[key], value)

        elif isinstance(format, tuple):  # deal with multi-valued container
            container_type, element_type = format
            self.assertIsInstance(response, container_type)
            if not isinstance(element_type, list):  # homogenous list
                for subitem in response:
                    self.validate(subitem, element_type)
            else:  # heterogenous list
                self.assertEqual(len(element_type), len(response), 'Incorrect list format')
                for subitem, subtype in zip(response, element_type):
                    self.validate(subitem, subtype)

        else:
            if response:
                self.assertIsInstance(response, format)


class PersonAPITest(ValidatedTestCase):

    url = URL + '/person/'

    # format section

    # POST /person
    create_person_format = {
        "id": unicode,
        "name": unicode
    }

    # GET /person
    get_person_list_format = (list, {
        "id": unicode,
        "name": unicode,
    })

    # GET /person/{person_id}
    get_person_format = {
        "country": unicode,
        "id": unicode,
        "name": unicode,
        "trackers": (list, unicode)
    }

    # PUT /person/{person_id}
    put_person_format = {
        "country": unicode,
        "id": unicode,
        "name": unicode,
    }

    def test_1_get_fake_person(self):
        r = requests.get(self.url+'/1-1-1-1')
        self.assertEqual(r.status_code, 404)

    def test_2_create_person(self):
        r, email = create_persons()
        self.assertEqual(r.status_code, 201)
        result = r.json()
        link = self.url + result['id']
        r2 = requests.get(link)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['id'], result['id'])
        self.validate(result, self.create_person_format)

    def test_create_duplicated_person(self):
        r, email = create_persons()
        r2, email2 = create_persons(email=email, name='Alexey')
        self.assertEqual(r.json()['id'], r2.json()['id'])

    def test_3_get_person(self):
        r = requests.get(self.url)
        self.validate(r.json(), self.get_person_list_format)
        p_id = r.json()[0]['id']
        r2 = requests.get(self.url + p_id)
        self.validate(r2.json(), self.get_person_format)
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
        self.validate(result, self.put_person_format)
        self.assertEqual(result['name'], 'Juan Carlos')
        self.assertEqual(result['country'], 'ME')


class PersonWithDataTest(unittest.TestCase):
    url = URL + '/person/'

    def setUp(self):
        # dirty dirty hack
        import psycopg2
        from gorynych import OPTS
        try:
            self.con = psycopg2.connect(database=OPTS['dbname'],
            user=OPTS['dbuser'], host=OPTS['dbhost'], password=OPTS[
                'dbpassword'])
        except Exception as e:
            raise unittest.SkipTest("Can't connect to database: %r" % e)
        self.cur = self.con.cursor()

    def tearDown(self):
        self.con.close()

    def test_add_change_person_phone(self):
        r, email = create_persons()
        self.assertEqual(r.status_code, 201)
        pid = r.json()['id']
        params = json.dumps(dict(phone='+7123456'))
        r = requests.put(self.url + pid, data=params)
        self.assertEqual(r.status_code, 200)
        self._check_phone_change(pid, '+7123456')

        params = json.dumps(dict(phone='+21'))
        r = requests.put(self.url + pid, data=params)
        self.assertEqual(r.status_code, 200)
        self._check_phone_change(pid, '+21')

    def _check_phone_change(self, pid, phone):
        self.cur.execute('''
         select data_type, data_value
         from person_data, person
         where
            person_id=%s
            and person.id = person_data.id
        ''', (pid, ))
        data = self.cur.fetchall()
        self.assertEqual(len(data), 1)

        data = {data[0][0]:data[0][1]}

        self.assertEqual(data['phone'], phone)
        self.con.commit()


class ParaglidersTest(ValidatedTestCase):

    # POST /contest/{contest_id}/paraglider
    post_paraglider_format = {
        "person_id": unicode,
        "glider": unicode,
        "contest_number": unicode
    }

    # GET /contest/{contest_id}/paraglider
    get_paraglider_list_format = {
        "person_id": unicode,
        "glider": unicode,
        "contest_number": unicode
    }

    # PUT /contest/{contest_id}/paraglider/{person_id}
    put_paraglider_format = {
        "person_id": unicode,
        "glider": unicode,
        "contest_number": unicode
    }

    def test_1_register_paragliders(self):
        try:
            cont_id = create_contest()[0].json()['id']
            pers_id = create_persons(reg_date='2012,12,12')[0].json()['id']
        except Exception:
            raise unittest.SkipTest("Contest and persons hasn't been created"
                                    ".")
        if not cont_id and not pers_id:
            self.skipTest("Can't test without contest and race.")
        r, cn = register_paraglider(pers_id, cont_id)
        self.assertEqual(r.status_code, 201)
        result = r.json()
        self.validate(result, self.post_paraglider_format)
        self.assertEqual(result['person_id'], pers_id)
        self.assertEqual(result['glider'], 'garlem')
        self.assertEqual(result['contest_number'], str(cn))

        # test get paragliders. it's supposed to be in separate testcase,
        # but I'm lazy to know how to store this cont_id.

        r2 = requests.get('/'.join((URL, 'contest', cont_id,
                                    'paraglider')))
        self.assertEqual(r2.status_code, 200)
        result2 = r2.json()[0]
        self.validate(result2, self.get_paraglider_list_format)
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
        self.validate(result, self.put_paraglider_format)
        self.assertEqual(result['contest_number'], '13')
        self.assertEqual(result['glider'], 'marlboro')


class ContestRaceTest(ValidatedTestCase):
    # for internal use
    _checkpoints_format = {
        "type": unicode,
        "features": (list, {
            "geometry": {
                "type": unicode,
                "coordinates": (list, float),
            },
            "type": unicode,
            "properties": {
                "open_time": int,
                "close_time": int,
                "checked_on": unicode,
                "name": unicode,
                "radius": int,
                "checkpoint_type": unicode,
            }
        })
    }

    # POST /contest/{contest_id}/race
    create_race_format = {
        "title": unicode,
        "type": unicode,
        "id": unicode,
        "start_time": int,
        "end_time": int
    }

    # GET /contest/{contest_id}/race/{race_id}
    get_race_format = {
        "race_title": unicode,
        "country": unicode,
        "start_time": int,
        "end_time": int,
        "contest_title": unicode,
        "optdistance": unicode,
        "timeoffset": unicode,
        "checkpoints": _checkpoints_format

    }

    # GET /contest/{contest_id}/race
    get_race_list_format = (list, {
        "start_time": int,
        "end_time": int,
        "title": unicode,
        "type": unicode,
        "id": unicode,
    })

    # PUT /contest/{contest_id}/race/{race_id}
    put_race_format = {
        "race_title": unicode,
        "start_time": int,
        "end_time": int,
        "checkpoints": _checkpoints_format
    }

    # GET /contest/{contest_id}/race/{race_id}/paragliders
    get_race_paragliders_format = (list, {
        "name": unicode,
        "country": unicode,
        "tracker": unicode,
        "contest_number": unicode,
        "person_id": unicode,
        "glider": unicode
    })

    def setUp(self):
        try:
            c_, t_ = create_contest(title='Contest with checkpoints and race')
            p_, e = create_persons()
            c_id = c_.json()['id']
            p_id = p_.json()['id']
            i, cn = register_paraglider(p_id, c_id)
        except:
            raise unittest.SkipTest("I need contest and paraglider for test")
        if not (p_id and c_id):
            raise unittest.SkipTest("I need contest and paraglider for test")
        self.c_id = c_id
        self.p_id = p_id
        self.cn = cn

    def test_create_read_race(self):
        # POST /contest/{contest_id}/race
        chs = create_geojson_checkpoints()
        r = create_race(self.c_id, chs, race_type='opendistance', bearing=12)
        result = r.json()
        self.validate(result, self.create_race_format)
        self.assertEqual(r.status_code, 201)
        self.assertDictContainsSubset({'type':'opendistance',
                                       'title':'Task 8',
                                       'start_time': 1347711300,
                                       'end_time': 1347732000
                                       }, result)

        # GET /contest/{contest_id}/race/{race_id}
        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race',
            result['id'])))
        self.assertEqual(r.status_code, 200)
        result = r.json()
        self.validate(result, self.get_race_format)
        self.assertEqual(result['race_type'], 'opendistance')
        self.assertEqual(result['bearing'], 12)
        self.assertEqual(result['start_time'], 1347711300)
        self.assertEqual(result['end_time'], 1347732000)
        self.assertEqual(result['race_title'], 'Task 8')
        self.assertEqual(result['checkpoints'], json.loads(chs))

    def test_get_race_list(self):
        try:
            race_id = create_race(self.c_id, race_type='racetogoal'
                ).json()['id']
        except Exception as error:
            raise unittest.SkipTest("Something went wrong and I need race "
                                    "for test: %r" % error)
        if not race_id:
            raise unittest.SkipTest("I need race for test")

        # GET /contest/{contest_id}/race
        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race')))
        self.validate(r.json(), self.get_race_list_format)
        self.assertEqual(r.status_code, 200)
        self.assertDictContainsSubset({'type':'racetogoal',
                                       'title':'Task 8',
                                       'start_time': 1347711300,
                                       'end_time': 1347732000}, r.json()[0])

    def test_change_race(self):
        try:
            race_id = create_race(self.c_id, race_type='opendistance',
                bearing=12).json()['id']
        except Exception as error:
            raise unittest.SkipTest("Something went wrong and I need race "
                                    "for test: %r" % error)

        # PUT /contest/{contest_id}/race/{race_id}
        new_ch_list = create_checkpoints()
        new_ch_list[0].name = 'HAHA'
        for i, item in enumerate(new_ch_list):
            new_ch_list[i] = item.__geo_interface__
        params = dict(title='Changed race', bearing=8, checkpoints=json
            .dumps({'type': 'FeatureCollection', 'features': new_ch_list}))
        r = requests.put('/'.join((URL, 'contest', self.c_id, 'race', race_id)),
                         data=json.dumps(params))
        self.validate(r.json(), self.put_race_format)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['race_title'], u'Changed race')
        self.assertEqual(r.json()['bearing'], 8)
        self.assertEqual(r.json()['checkpoints']['features'],
                         json.loads(json.dumps(new_ch_list)))

        # Test POST /contest/{id}/race/{id}/track_archive
        r = requests.post('/'.join((URL, 'contest', self.c_id, 'race', race_id,
                   'track_archive')), data=json.dumps({'url':'http://airtribune.com/1'}),
                   headers={'Content-Type': 'application/json'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['result'],
            "Archive with url http://airtribune.com/1 added.")

    def test_get_race_paragliders(self):
        try:
            race_id = create_race(self.c_id).json()['id']
        except Exception as error:
            raise unittest.SkipTest("Something went wrong and I need race "
                                    "for test: %r" % error)
        if not race_id:
            raise unittest.SkipTest("I need race for test")

        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race',
        race_id)))
        self.validate(r.json(), self.get_race_format)
        self.assertEqual(r.status_code, 200)

        # GET /contest/{contest_id}/race/{race_id}/paragliders
        r = requests.get('/'.join((URL, 'contest', self.c_id, 'race', race_id,
                                    'paragliders')))
        self.validate(r.json(), self.get_race_paragliders_format)
        self.assertEqual(r.status_code, 200)
        self.assertDictContainsSubset({'glider':'garlem',
                                       'contest_number':str(self.cn),
                                       'name':'V. Doe', 'country':'SS'},
                                      r.json()[0])


class TrackerTest(ValidatedTestCase):
    url = URL + '/tracker'

    # format section

    # POST /tracker
    create_tracker_format = {
        "device_id": unicode,
        "id": unicode,
        "device_type": unicode,
        "name": unicode
    }

    # GET /tracker
    get_tracker_list_format = (list, {
        "last_point": (list, [float, float, int, int, int, float]),
        "device_id": unicode,
        "name": unicode,
        "device_type": unicode,
        "id": unicode,
    })

    # GET /tracker/{tracker_id}
    get_tracker_format = {
        "last_point": (list, [float, float, int, int, int, float]),
        "device_id": unicode,
        "name": unicode,
        "id": unicode,
    }

    # PUT /tracker/{tracker_id}
    put_tracker_format = {
        "last_point": (list, [float, float, int, int, int, float]),
        "device_id": unicode,
        "name": unicode,
        "id": unicode,
    }


    def test_create(self):
        device_id = str(random.randint(1, 1000))
        params = dict(device_id=device_id,
            device_type='tr203', name='a03')
        # POST /tracker
        r = requests.post(self.url, data=json.dumps(params), headers={'Content-Type': 'application/json'})
        result = r.json()
        self.validate(result, self.create_tracker_format)
        self.assertEqual(r.status_code, 201)
        self.assertTupleEqual((result['device_id'], result['device_type'],
            result['name'], result['id']), (device_id, 'tr203', 'a03',
            'tr203-' + device_id))

        # GET /tracker
        r = requests.get(self.url)
        self.assertEqual(r.status_code, 200)
        r = r.json()
        self.validate(r, self.get_tracker_list_format)
        self.assertIsInstance(r, list)
        self.assertGreaterEqual(len(r), 1)
        device = None
        for item in r:
            if item['device_type'] == 'tr203':
                device = item['device_type']
        self.assertIsNotNone(device)

        # GET /tracker/{tracker_id}
        tid = r[0]['id']
        r = requests.get('/'.join((self.url, tid)))
        self.validate(r.json(), self.get_tracker_format)
        self.assertEqual(r.status_code, 200)

        # PUT /tracker/{tracker_id}
        params = json.dumps(dict(name='hello'))
        r = requests.put('/'.join((self.url, tid)), data=params)
        self.assertEqual(r.status_code, 200)
        r = r.json()
        self.validate(r, self.put_tracker_format)
        self.assertEqual(r['name'], 'hello')

    def test_assign_tracker_to_person(self):
        try:
            p, email = create_persons()
            pid = p.json()['id']
            device_id = str(random.randint(1, 1000))
            params = dict(device_id=device_id,
                device_type='tr203')
            r = requests.post(self.url, data=json.dumps(params), headers={'Content-Type': 'application/json'})
            tid = r.json()['id']
        except Exception as e:
            raise unittest.SkipTest("Need person and tracker for test.")
        if not tid and not pid:
            raise unittest.SkipTest("No ids for test.")

        # assign
        params = json.dumps(dict(assignee=str(pid), contest_id='cont'))
        r = requests.put('/'.join((self.url, tid)), data=params)
        self.validate(r.json(), self.get_tracker_format)
        self.assertEqual(r.status_code, 200)

        p = requests.get('/'.join((URL, 'person', pid)))
        self.assertEqual(p.status_code, 200)
        self.assertEqual(p.json()['trackers'], [[tid, 'cont']])

        # unassign
        params = json.dumps(dict(assignee='', contest_id='cont'))
        r = requests.put('/'.join((self.url, tid)), data=params)
        self.validate(r.json(), self.get_tracker_format)
        self.assertEqual(r.status_code, 200)

        p = requests.get('/'.join((URL, 'person', pid)))
        self.assertEqual(p.status_code, 200)
        self.assertEqual(p.json()['trackers'], [])

    def test_duplicate(self):
        device_id = str(random.randint(1, 1000))
        params = dict(device_id=device_id,
            device_type='tr203')
        r = requests.post(self.url, data=json.dumps(params), headers={'Content-Type': 'application/json'})
        tid = r.json()['id']

        # duplicate
        r1 = requests.post(self.url, data=json.dumps(params), headers={'Content-Type': 'application/json'})
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.json()['id'], tid)


class ValidatedTransportTestCase(ValidatedTestCase):
    """
    A common base class for TestTransportAPI and ContestTransportTest
    """

    # POST /transport
    create_transport_format = {
        "title": unicode,
        "type": unicode,
        "description": unicode,
        "id": unicode
    }

    # GET /transport
    get_transport_list_format = (list, {
        "title": unicode,
        "type": unicode,
        "description": unicode,
        "id": unicode
        })

    # GET /transport/{transport_id}
    get_transport_format = {
        "title": unicode,
        "type": unicode,
        "description": unicode,
        "id": unicode
    }

    # PUT /transport/{transport_id}
    put_transport_format = {
        "title": unicode,
        "type": unicode,
        "description": unicode,
        "id": unicode
    }

    # POST /contest/{contest_id}/transport

    add_to_contest_format = (list, unicode)


class TestTransportAPI(ValidatedTransportTestCase):
    url = URL + '/transport'

    def test_create(self):
        r = create_transport(ttype='bus', title='Yellow bus',
            description='Cool yellow bus with condition')
        self.validate(r.json(), self.create_transport_format)
        self.assertEqual(r.status_code, 201)
        self.assertDictContainsSubset({'title': 'Yellow bus', 'type': 'bus',
            'description': 'Cool yellow bus with condition'}, r.json())

    def test_get_list(self):
        try:
            r = create_transport(ttype='car', title='Good car',
                description='car')
            tid = r.json()['id']
        except Exception:
            raise unittest.SkipTest("Can't create transport.")
        if not tid:
            raise unittest.SkipTest("Transport id needed for test.")

        r = requests.get(self.url)
        self.assertEqual(r.status_code, 200)
        result = r.json()
        self.validate(result, self.get_transport_list_format)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        ids = []
        for t in result:
            ids.append(t['id'])
        self.assertIn(tid, ids)

    def test_get_transport(self):
        try:
            r = create_transport(ttype='car', title='Good car',
                description='card')
            tid = r.json()['id']
        except Exception:
            raise unittest.SkipTest("Can't create transport.")
        if not tid:
            raise unittest.SkipTest("Transport id needed for test.")

        r = requests.get('/'.join((self.url, tid)))
        self.validate(r.json(), self.get_transport_format)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['id'], tid)
        self.assertDictContainsSubset({'title': 'Good car',
            'description':'Card', 'type':'car'}, r.json())

    def test_change_transport(self):
        try:
            r = create_transport(ttype='car', title='Good car',
                description='car')
            tid = r.json()['id']
        except Exception:
            raise unittest.SkipTest("Can't create transport.")
        if not tid:
            raise unittest.SkipTest("Transport id needed for test.")

        # change it
        params = json.dumps(dict(type='bus', title='A bus.',
            description='New description.'))
        r = requests.put('/'.join((self.url, tid)), data=params)
        self.validate(r.json(), self.put_transport_format)
        self.assertEqual(r.status_code, 200)
        self.assertDictContainsSubset({'type':'bus', 'title':'A bus.',
            'description':'New description.','id':tid}, r.json())

        # get it from API
        r = requests.get('/'.join((self.url, tid)))
        self.validate(r.json(), self.get_transport_format)
        self.assertEqual(r.status_code, 200)
        self.assertDictContainsSubset({'type':'bus', 'title':'A bus.',
            'description':'New description.','id':tid}, r.json())


class ContestTransportTest(ValidatedTransportTestCase):
    url = URL + '/contest'

    def setUp(self):
        try:
            c_, t_ = create_contest(title='Contest with transport')
            tr_ = create_transport()
        except:
            raise unittest.SkipTest("I need contest for test")
        self.c_id = c_.json()['id']
        self.tr_id = tr_.json()['id']

    def tearDown(self):
        del self.c_id
        del self.tr_id

    def test_add_transport_to_contest(self):
        r = requests.post('/'.join((self.url, self.c_id, 'transport')),
            data=json.dumps(dict(transport_id=self.tr_id)),
            headers={'Content-Type': 'application/json'})
        self.validate(r.json(), self.add_to_contest_format)
        self.assertEqual(r.status_code, 201)
        self.assertIn(self.tr_id, r.json())

        # GET /contest/{contest_id}/transport
        r = requests.get('/'.join((self.url, self.c_id, 'transport')))
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)
        self.assertIsInstance(r.json(), list)

    def test_get_race_transport(self):
        try:
            # Create paraglider for contest.
            p_, e = create_persons()
            p_id = p_.json()['id']
            i, cn = register_paraglider(p_id, self.c_id)
            # Append transport to contest.
            r = requests.post('/'.join((self.url, self.c_id, 'transport')),
                data=json.dumps(dict(transport_id=self.tr_id)),
                headers={'Content-Type': 'application/json'})
            # Create tracker and assign it to transport.
            params = dict(device_id=random.randint(1, 1000),
                device_type='tr203')
            r = requests.post('/'.join((URL, 'tracker')), data=json.dumps(params))
            tid = r.json()['id']
            params = json.dumps(dict(assignee=str(self.tr_id),
                contest_id='cont'))
            r = requests.put('/'.join((URL, 'tracker', tid)), data=params)
            # Create race.
            race_id = create_race(self.c_id).json()['id']
        except Exception as error:
            raise unittest.SkipTest("Something went wrong and I need race "
                                    "for test: %r" % error)

        r = requests.get('/'.join((self.url, self.c_id, 'race', race_id,
                        'transport')))
        self.assertEqual(r.status_code, 200)
        res = r.json()
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 1)
        self.assertEqual(tid, res[0]['tracker'])
        self.assertEqual(self.tr_id, res[0]['id'])



if __name__ == '__main__':
    unittest.main()
