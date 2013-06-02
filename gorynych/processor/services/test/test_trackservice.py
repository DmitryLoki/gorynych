import json
import os
import sys

from shapely.geometry import Point
import mock
import requests

from twisted.internet import defer
from twisted.trial import unittest

from gorynych.test.test_info import create_geojson_checkpoints
from gorynych.common.domain.types import Checkpoint
from gorynych.processor import trfltfs
from gorynych.processor.services.trackservice import ProcessorService
from gorynych.info.domain.ids import RaceID
from gorynych.common.domain.events import ParagliderFoundInArchive, TrackArchiveUnpacked


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

def raise_callback():
    d = defer.Deferred()
    d.addCallback(lambda x: None)
    d.callback(1)
    return d

class ParsingTest(unittest.TestCase):
    def setUp(self):
        raise unittest.SkipTest("skipped")

    def test_parsing(self):
        # create contest, person, register paragliders, create race:
        cont_id = create_contest()
        register_paragliders_on_contest(cont_id)
        race = create_race(cont_id,
                           create_geojson_checkpoints(create_checkpoints()))
        print race.text
        race_id = race.json()['id']
        # self.init_task(race_id)
        r = requests.post('/'.join((URL, 'contest', cont_id, 'race',
                                    race_id, 'track_archive')),
                                      data={'url': 'http://airtribune.com/1'})
        print r.text
        print r.status_code

    def init_task(self, race_id):
        task = trfltfs.init_task(race_id)
        self.assertIsInstance(task, dict)
        self.assertTrue(task.has_key('window_is_open'))


class TestProcessorService(unittest.TestCase):
    def setUp(self):
        self.ps = ProcessorService(1)
        self.pe_patch = mock.patch('gorynych.processor.services.trackservice.pe')
        self.pe = self.pe_patch.start()

    def tearDown(self):
        self.pe_patch.stop()

    def test_inform_about_paragliders(self):
        i0 = {'person_id': 'person_id', 'trackfile':'1.igc',
            'contest_number': '1'}
        i1, i2 = [], []
        rid = RaceID()
        es = mock.Mock()
        self.pe.event_store.return_value = es
        es.persist.return_value = raise_callback()
        result = self.ps._inform_about_paragliders([[i0], i1, i2], rid)

        ev1 = ParagliderFoundInArchive(rid, payload=i0)
        ev2 = TrackArchiveUnpacked(rid, payload=[[i0], i1, i2])
        expected = [mock.call(ev1), mock.call(ev2)]
        self.assertListEqual(es.persist.mock_calls, expected)

