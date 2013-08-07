# encoding: utf-8

import mock
from twisted.trial import unittest

from gorynych.info.domain.ids import TrackerID
from gorynych.info.domain.race import Race
from gorynych.info.domain.services import ContestRaceService
from gorynych.info.domain.test.helpers import create_contest, create_checkpoints,\
    create_transport, create_person, create_race
from gorynych.common.domain.types import checkpoint_from_geojson


class ContestRaceSerivceTest(unittest.TestCase):

    @mock.patch('gorynych.common.infrastructure.persistence.event_store')
    def test_create_new_race(self, patched):
        event_store = mock.Mock()
        patched.return_value = event_store

        chps = create_checkpoints()
        cont = create_contest(start_time=chps[0].open_time - 3600,
                              end_time=chps[-1].close_time + 3600)
        # make this list of aggregates list of tuples
        t = create_transport('bus')
        transport_list = [(t.type, t.title, t.description,
                           TrackerID(TrackerID.device_types[0],
                                     '123456789012345'), t.id)]
        person_list = [create_person(name='John', surname='Doe'),
                       create_person(name='Jane', surname='Doe')]
        for i, p in enumerate(person_list):
            cont.register_paraglider(p.id, 'flying piece of wood', i)

        race_params = {
            'title': 'My task',
            'race_type': 'racetogoal',
            'checkpoints': chps
        }

        new_race = ContestRaceService().create_new_race_for_contest(cont,
                                                                    person_list,
                                                                    transport_list,
                                                                    race_params)
        self.assertTrue(isinstance(new_race, Race))
        self.assertEquals(new_race.title, race_params['title'])
        self.assertEquals(new_race.type, race_params['race_type'])
        self.assertEquals(new_race.checkpoints, chps)

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

        changed_race = ContestRaceService().change_contest_race(r, race_params)
        self.assertEquals(changed_race.title, race_params['race_title'])
        self.assertEquals(changed_race.checkpoints[0],
                          checkpoint_from_geojson(race_params['checkpoints']['features'][0]))
        self.assertEquals(changed_race.type, r.type)
