import json
from twisted.trial import unittest
import requests
import os
import sys
from shapely.geometry import Point

from gorynych.test.test_info import create_geojson_checkpoints
from gorynych.common.domain.types import Checkpoint


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
        if ch[6]:
            open_time = int(ch[5])
            ch_type = 'ss'
        if ch[7]:
            ch_type = 'es'
        if int(key) == 1:
            ch_type = 'to'
        if int(key) == 7:
            ch_type = 'goal'
        result.append(Checkpoint(ch[3], Point(ch[0], ch[1]), ch_type,
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
                           email='s@s.ru')
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


class TestCase(unittest.TestCase):
    def test_parsing(self):
        # create contest, person, register paragliders, create race:
        cont_id = create_contest()
        register_paragliders_on_contest(cont_id)
        create_race(cont_id, create_checkpoints())


if __name__ == '__main__':
    unittest.main()
