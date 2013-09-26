import random
import requests
import time
import json
import socket
import string
from twisted.trial import unittest
from operator import xor

from gorynych.info.domain.test.helpers import create_checkpoints

INFO_URL = 'http://localhost:8085'
VIZ_URL = 'http://localhost:8886'

# Correct the port values if needed
RECEIVER = {
    'tr203': 9999,
    'telt_gh3000': 9998,
    'new_mobile': 10001
}


def get_random_imei():
    return ''.join([random.choice(string.digits) for i in xrange(15)])


def create_contest(title='Contest with paragliders'):
    title = title + '_' + str(random.randint(1, 1000000))
    params = dict(title=title, start_time=1,
                  end_time=1999999999,
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
    for item in ch_list:
        item.open_time = 1
        item.close_time = 1999999999
    for i, item in enumerate(ch_list):
        ch_list[i] = item.__geo_interface__
    return json.dumps(dict(type='FeatureCollection',
                           features=ch_list))


def create_race(contest_id, checkpoints=None, race_type='racetogoal',
                bearing=None):
    if not checkpoints:
        checkpoints = create_geojson_checkpoints()
    params = dict(title="Task 100", race_type=race_type,
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


def add_tracker(tracker_type, tracker_id):
    params = dict(device_id=tracker_id,
                  device_type=tracker_type)
    r = requests.post('/'.join([INFO_URL, 'tracker']), data=params)
    if not r.status_code == 201:
        raise Exception
    return r


def assign_tracker(pers_id, cont_id, tracker_type, tracker_id):
    add_tracker(tracker_type, tracker_id)
    tracker_name = '-'.join([tracker_type, tracker_id])
    params = dict(name=tracker_name,
                  assignee=pers_id,
                  contest_id=cont_id)
    r = requests.put(
        '/'.join([INFO_URL, 'tracker', tracker_name]), data=json.dumps(params))
    if not r.status_code == 200:
        raise Exception
    return r


class TestTrack(unittest.TestCase):

    def setUp(self):
        try:
            c_, t_ = create_contest(title='Contest with checkpoints and race')
            p_, e = create_persons()
            c_id = c_.json()['id']
            p_id = p_.json()['id']
            assign_tracker(p_id, c_id, self.device_type, self.imei)
            i, cn = register_paraglider(p_id, c_id)
            r = create_race(c_id)
            r_id = r.json()['id']
        except Exception as e:
            raise unittest.SkipTest("Something has been fucked up during the test preparation: {}".format(
                e.message))
        if not (p_id and c_id and r_id):
            raise unittest.SkipTest("Contest, race or paraglider are missing")
        self.c_id = c_id
        self.p_id = p_id
        self.cn = cn
        self.r_id = r_id

    def _call_tracks(self):
        r = requests.get(
            '/'.join([INFO_URL, 'race', self.r_id, 'tracks']), params={'type': 'online'})
        return r.json()

    def _call_timeline(self):
        r = requests.get(
            '/'.join([VIZ_URL, 'group', self.r_id + '_online']),
            params={
                'from_time': 0,
                'to_time': 1999999999
            })
        return r.json()


class TestTR203Tracker(TestTrack):
    device_type = 'tr203'

    def setUp(self):
        self.imei = get_random_imei()
        super(TestTR203Tracker, self).setUp()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver = ('localhost', RECEIVER['tr203'])

    def _make_message(self, payload):
        msg = 'GSr,' + self.imei + ',' + payload
        nmea = map(ord, msg)
        check = reduce(xor, nmea)
        msg += '*' + chr(check).encode('hex') + '!'
        return msg

    def test_track_handling(self):
        # a track should be created after the first message.
        msg = self._make_message(
            '3,250713,212244,E024.705360,N42.648187,440,0,0.8,46')
        self.sock.sendto(msg, self.receiver)

        print 'Please wait for about a minute while gorynych is processing track...'
        time.sleep(70)

        tracks = self._call_tracks()
        self.assertEquals(len(tracks), 1)

        timeline = self._call_timeline()
        self.assertTrue(u'1374783764' in timeline['timeline'])
        self.assertEquals(len(timeline['timeline'].keys()), 1)

        # the second message should be appended to the same track.
        second_msg = self._make_message('3,250713,212544,E014.705360,N44.648187,440,0,0.8,46')
        self.sock.sendto(second_msg, self.receiver)

        print 'Please wait AGAIN...'
        time.sleep(70)

        tracks = self._call_tracks()
        self.assertEquals(len(tracks), 1)

        timeline = self._call_timeline()
        self.assertTrue(u'1374783764' in timeline['timeline'])
        self.assertTrue(u'1374783944' in timeline['timeline'])
        self.assertEquals(len(timeline['timeline'].keys()), 2)
