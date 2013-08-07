# encoding: utf-8

import json

from twisted.internet import defer
from gorynych.info.domain import contest, race
from gorynych.common.infrastructure import persistence
from gorynych.common.domain.events import ContestRaceCreated
from gorynych.common.domain.types import checkpoint_from_geojson


class ContestRaceService(object):

    def create_new_race_for_contest(self, cont, person_list, transport_list, race_params):
        paragliders = cont.paragliders
        persons = {p.id: p for p in person_list}
        plist = []

        for key in paragliders:
            pers = persons[key]
            plist.append(contest.Paraglider(key, pers.name, pers.country,
                         paragliders[key]['glider'],
                         paragliders[key]['contest_number'],
                         pers.trackers.get(cont.id)))

        factory = race.RaceFactory()
        r = factory.create_race(race_params['title'], race_params['race_type'],
                                cont.timezone, plist,
                                race_params['checkpoints'],
                                bearing=race_params.get('bearing'),
                                transport=transport_list,
                                timelimits=(cont.start_time, cont.end_time))
        return r

    def change_contest_race(self, contest_race, race_params):
        '''
        Change information about race in contest.
        @param params:
        @type params:
        @return: Race
        @rtype:
        '''
        if 'checkpoints' in race_params:
            if isinstance(race_params['checkpoints'], (str, unicode)):
                try:
                    ch_list = json.loads(
                        race_params['checkpoints'])['features']
                except Exception as e:
                    raise ValueError(
                        "Problems with checkpoint reading: %r .Got %s, %r" %
                                    (e, type(race_params['checkpoints']),
                                        race_params['checkpoints']))
            elif isinstance(race_params['checkpoints'], dict):
                ch_list = race_params['checkpoints']['features']
            else:
                raise ValueError(
                    "Problems with checkpoint reading: got %s, %r" %
                    (type(race_params['checkpoints']), race_params['checkpoints']))
            checkpoints = []
            for ch in ch_list:
                checkpoints.append(checkpoint_from_geojson(ch))
            contest_race.checkpoints = checkpoints
        if 'race_title' in race_params:
            contest_race.title = race_params['race_title']
        if 'bearing' in race_params:
            contest_race.bearing = race_params['bearing']
        return contest_race
