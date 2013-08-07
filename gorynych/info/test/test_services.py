import mock
import time
from copy import deepcopy
from twisted.trial import unittest

from gorynych.info.domain.ids import TrackerID, PersonID, TransportID
from gorynych.info.domain.race import Race
from gorynych.info.domain.test.helpers import create_contest, create_checkpoints,\
    create_transport, create_person, create_race
from gorynych.common.domain.types import checkpoint_from_geojson

from gorynych.info.domain.contest import create_race_for_contest,\
    change_contest_participant
from gorynych.info.domain.race import change_race


class ContestRaceCreationTest(unittest.TestCase):

    def setUp(self):
        try:
            self.chps = create_checkpoints()
            self.cont = create_contest(
                start_time=self.chps[0].open_time - 3600,
                end_time=self.chps[-1].close_time + 3600)
            self.trnsp = create_transport('bus')
            self.person_list = [create_person(name='John', surname='Doe'),
                                create_person(name='Jane', surname='Doe')]
        except Exception as e:
            raise unittest.SkipTest("Either contest or persons or transport failed:\
                skipping the test. \nException: {}".format(e.message))

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_create_new_race(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        # make this list of aggregates list of tuples
        for i, p in enumerate(self.person_list):
            self.cont.register_paraglider(p.id, 'flying piece of wood', i)

        transport_list = [(
            self.trnsp.type, self.trnsp.title, self.trnsp.description,
            TrackerID(TrackerID.device_types[0],
                      '123456789012345'), self.trnsp.id)]

        race_params = {
            'title': 'My task',
            'race_type': 'racetogoal',
            'checkpoints': self.chps
        }

        new_race = create_race_for_contest(self.cont,
                                           self.person_list,
                                           transport_list,
                                           race_params)
        self.assertTrue(isinstance(new_race, Race))
        self.assertEquals(new_race.title, race_params['title'])
        self.assertEquals(new_race.type, race_params['race_type'])
        self.assertEquals(new_race.checkpoints, self.chps)

        # checking people
        self.assertEquals(
            len(self.person_list), len(new_race.paragliders.items()))
        for i, p in enumerate(self.person_list):
            self.assertEquals(p.id, new_race.paragliders[i].person_id)
            self.assertEquals(i, new_race.paragliders[i].contest_number)

        # checking transport
        self.assertEquals(1, len(new_race.transport))
        race_trnsp = new_race.transport[0]
        self.assertEquals(race_trnsp['transport_id'], self.trnsp.id)
        self.assertEquals(race_trnsp['type'], self.trnsp.type)
        self.assertEquals(race_trnsp['description'], self.trnsp.description)


class RaceServiceTest(unittest.TestCase):

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_change_race(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        r = create_race()
        race_params = {
            'race_title': 'My other task',
            'race_type': 'somewtf',
            'checkpoints': {
                "features": [
                    {
                        "geometry": {
                            "type": "Point",
                            "coordinates": [42.687497, 24.750131]
                        },
                        "type": "Feature",
                        "properties": {
                            "close_time": 1374238200,
                            "radius": 400,
                            "name": "25S145",
                            "checkpoint_type": "to",
                            "open_time": 1374223800
                        }
                    }
                ]
            }
        }

        changed_race = change_race(r, race_params)
        self.assertEquals(changed_race.title, race_params['race_title'])
        self.assertEquals(changed_race.checkpoints[0],
                          checkpoint_from_geojson(race_params['checkpoints']['features'][0]))
        self.assertEquals(changed_race.type, r.type)


class ContestServiceTest(unittest.TestCase):

    def setUp(self):
        self.cont = create_contest(time.time(), time.time() + 3600)

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_register_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        alone_cont = deepcopy(self.cont)
        pid = PersonID()
        populated_cont = self.cont.register_paraglider(pid,
                                                       'glider',
                                                       11)
        self.assertFalse(alone_cont.paragliders)
        self.assertTrue(populated_cont.paragliders)

        pgl = populated_cont.paragliders
        self.assertEquals(pgl.keys()[0], pid)
        self.assertEquals(pgl[pid]['role'], 'paraglider')
        self.assertEquals(pgl[pid]['glider'], 'glider')
        self.assertEquals(pgl[pid]['contest_number'], 11)

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_add_transport(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        alone_cont = deepcopy(self.cont)
        tid = TransportID()
        populated_cont = self.cont.add_transport(tid)

        self.assertFalse(alone_cont.transport)
        self.assertIn(tid, populated_cont.transport)

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_change_paraglider(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        pid = PersonID()
        cont = self.cont.register_paraglider(pid,
                                             'glider',
                                             11)
        changed_cont = change_contest_participant(cont, dict(glider='noglider',
                                                             contest_number=21,
                                                             person_id=pid))

        pgl = changed_cont.paragliders

        self.assertEquals(pgl.keys()[0], pid)
        self.assertEquals(pgl[pid]['glider'], 'noglider')
        self.assertEquals(pgl[pid]['contest_number'], 21)
