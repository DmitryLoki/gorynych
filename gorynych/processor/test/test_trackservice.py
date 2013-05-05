import json
import cPickle
import os
import sys
from random import randint

from shapely.geometry import Point
from txpostgres import txpostgres
import mock
import requests

from twisted.internet import defer
from twisted.trial import unittest

from gorynych.test.test_info import create_geojson_checkpoints
from gorynych.common.domain.types import Checkpoint
from gorynych.processor import trfltfs
from gorynych.processor.services import trackservice
from gorynych import OPTS


URL = 'http://localhost:8085'
data = open(os.path.join(os.path.dirname(__file__), '1120-5321.json'),
                'r').read()
DATA = json.loads(data)

def create_checkpoints():
    ch_keys = DATA['waypoints'].keys()
    ch_keys.sort()
    result = []
    for key in ch_keys:
        # list: ["lat", u'lon', u'radius', u'name', 'dist', ss_open_time,
        # 'is_start', 'is_finish',
        ch = DATA['waypoints'][key]
        open_time = int(DATA['task_start'])
        close_time = int(DATA['task_end'])
        ch_type = 'ordinal'
        if int(ch[6]):
            open_time = int(ch[5])
            ch_type = 'ss'
        elif int(ch[7]):
            ch_type = 'es'
        if int(key) == 1:
            ch_type = 'to'
        if int(key) == 7:
            ch_type = 'goal'
        result.append(Checkpoint(ch[3], Point(float(ch[0]), float(ch[1])),
                                 ch_type,
            (open_time, close_time), int(ch[2])))
    return result


def create_contest(title='Test TrackService contest'):
    params = dict(title=title, start_time=1,
                  end_time=sys.maxint,
                  place = 'La France', country='ru',
                  hq_coords='43.3,23.1', timezone='Europe/Paris')
    r = requests.post(URL + '/contest', data=params)
    return r.json()['id']


def register_paragliders_on_contest(cont_id):
    pilots = DATA['pilots']
    for key in pilots.keys():
        params = dict(name=pilots[key]['name'].split(' ')[0],
                           surname=pilots[key]['name'].split(' ')[1],
                           country='ru',
                           email='s@s.ru', reg_date='2012,12,12')
        r = requests.post(URL + '/person', data=params)
        pers_id = r.json()['id']
        params = dict(person_id=pers_id, glider='mantra',
                      contest_number=str(key))
        r = requests.post('/'.join((URL, 'contest', cont_id,
                                'paraglider')), data=params)


def create_race(contest_id, checkpoints=None):
    if not checkpoints:
        checkpoints = create_geojson_checkpoints()
    params = dict(title="Test TrackService Task", race_type='racetogoal',
                  checkpoints=checkpoints)
    return requests.post('/'.join((URL, 'contest', contest_id, 'race')),
                         data=params)


class ParsingTest(unittest.TestCase):
    def test_parsing(self):
        # create contest, person, register paragliders, create race:
        cont_id = create_contest()
        register_paragliders_on_contest(cont_id)
        race = create_race(cont_id,
                           create_geojson_checkpoints(create_checkpoints()))
        print race.text
        race_id = race.json()['id']
        self.init_task(race_id)
        r = requests.post('/'.join((URL, 'contest', cont_id, 'race',
                                    race_id, 'track_archive')),
                                      data={'url': 'http://airtribune.com/1'})
        print r.text
        print r.status_code

    def init_task(self, race_id):
        task = trfltfs.init_task(race_id)
        print task
        self.assertIsInstance(task, dict)
        self.assertTrue(task.has_key('window_is_open'))


# class PrepareDataTest(unittest.TestCase):
#     def setUp(self):
#         self.skipTest("Don't has time for correct test.")
#         filename = '/Users/asumch2n/PycharmProjects/gorynych/8bec41ac-d96d-41c9-8f45-9ed74890c12a.processed.pickle'
#         f = open(filename, 'rb')
#         self.tracs = cPickle.load(f)
#         f.close()
#         self.track_number = randint(0, 100)
#         self.tid = long(randint(0, 1000000))
#
#     def test_prepare_data(self):
#         trac = self.tracs[self.track_number]
#         data = trackservice.prepare_data((self.tid,), trac)
#         self.assertEqual(data.ndim, 1)
#         self.assertEqual(data.shape, (len(trac['alt']),))
#         self.assertEqual(data['id'][randint(0, 200)], self.tid)
#         print data[:5]
#
#     def test_prepare_binary(self):
#         trac = self.tracs[self.track_number]
#         data = trackservice.prepare_data((self.tid,), trac)
#         a = trackservice.prepare_binary(data)
#         f = open('prepare_binary', 'wb')
#         f.write(a.read())
#         f.close()
#
#     def test_prepare_text(self):
#         trac = self.tracs[self.track_number]
#         data = trackservice.prepare_data((self.tid,), trac)
#         a = trackservice.prepare_text(data)
#         f = open('prepare_text', 'w')
#         f.write(a.read())
#         f.close()

# class TracksInsertionTest(unittest.TestCase):
#     def setUp(self):
#         self.pool = txpostgres.ConnectionPool(None, host=OPTS['db']['host'],
#                                               database=OPTS['db']['database'],
#                                               user=OPTS['db']['user'],
#                                               password=OPTS['db']['password'], min=5)
#         filename = '/Users/asumch2n/PycharmProjects/gorynych/8bec41ac-d96d-41c9-8f45-9ed74890c12a.processed.pickle'
#         f = open(filename, 'rb')
#         self.tracs = cPickle.load(f)
#         return self.pool.start()
#
#     def tearDown(self):
#         return self.pool.close()
#
#     @defer.inlineCallbacks
#     @mock.patch('gorynych.common.infrastructure.persistence.event_store')
#     def test_insert_offline_tracks(self, patched):
#         patched.return_value = mock.MagicMock()
#         race_id = '8bec41ac-d96d-41c9-8f45-9ed74890c12a'
#         trac = [self.tracs[4]]
#
#         serv = trackservice.TrackService(self.pool)
#         serv.poll_for_events = mock.Mock()
#         # yield serv.startService()
#         yield serv.insert_offline_tracks(trac, race_id)
