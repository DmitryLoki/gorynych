import random
import requests
import time
import json
import socket
from twisted.trial import unittest

from gorynych.info.domain.test.helpers import create_checkpoints

INFO_URL = 'http://localhost:8085'

# Correct the port values if needed
RECEIVER = {
    'tr203': 9999,
    'telt_gh3000': 9998,
    'new_mobile': 10001
}


def create_contest(title='Contest with paragliders'):
    title = title + '_' + str(random.randint(1, 1000000))
    params = dict(title=title, start_time=1,
                  end_time=int(time.time()),
                  place='La France', country='ru',
                  hq_coords='43.3,23.1', timezone='Europe/Paris')
    r = requests.post(INFO_URL + '/contest', data=params)
    if not r.status_code == 201:
        print r.text
    return r, title


def create_persons(reg_date=None, email=None, name=None, phone=None, udid=None):
    if not email:
        email = 'vasya@example.com' + str(random.randint(1, 1000000))
    if not name:
        name = 'Vasylyi'
    params = dict(name=name, surname='Doe', country='SS',
                  email=email, reg_date=reg_date)
    if phone:
        params.update({'phone': phone})
    if udid:
        params.update({'udid': udid})
    r = requests.post(INFO_URL + '/person', data=params)
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
    return requests.post('/'.join((INFO_URL, 'contest', contest_id, 'race')),
                         data=params)


def register_paraglider(pers_id, cont_id):
    cn = random.randint(1, 10000)
    params = dict(person_id=pers_id, glider='gArlem 88',
                  contest_number=str(cn))
    r = requests.post('/'.join((INFO_URL, 'contest', cont_id,
                                'paraglider')), data=params)
    if not r.status_code == 201:
        raise Exception
    return r, cn


class TestTrack(unittest.TestCase):

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


class TestTR203Tracker(TestTrack):
    def setUp(self):
        super(TestTR203Tracker).setUp()
        self.msg = 'GSr,011412001275167,3,250713,212244,E024.705360,N42.648187,440,0,0.8,46*7e!'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver = ('localhost', RECEIVER['tr203'])

    def test_one_message(self):
        """
        A track should be created after the first message.
        """
        self.sock.sendto(self.msg, self.receiver)
