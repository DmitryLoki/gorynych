'''
Functions used in other tests.
'''
import sys
from shapely.geometry import Point
from gorynych.common.domain.types import Checkpoint
from gorynych.info.domain import contest
from gorynych.info.domain.person import PersonID

__author__ = 'Boris Tsema'


def create_contest(start_time, end_time, id=None,
                   title='  Hello world  ',
                   place='Yrupinsk', country='rU', coords=(45.23, -23.22),
                   timezone='Europe/Moscow'):
    factory = contest.ContestFactory()
    cont = factory.create_contest(title, start_time, end_time, place,
        country, coords, timezone, id)
    return cont

def create_race(cont=None):
    if not cont:
        cont = create_contest(1, sys.maxint)
    pid1 = PersonID()
    pid2 = PersonID()
    cont.register_paraglider(pid1, 'mantrA 9', '757')
    cont.register_paraglider(pid2, 'gIn 9', '747')
    result = cont.new_race('racetogoal', create_checkpoints(), 'Test Race')
    return result


def create_checkpoints():
    # also used in test_info
    ch1 = Checkpoint('D01', Point(43.9785, 6.48), 'TO',
                     (1347711300, 1347716700), 1)
    ch2 = Checkpoint('D01', Point(43.9785, 6.48), 'ss',
                     (1347714900, 1347732000), 3000)
    ch2_ordinal = Checkpoint('B20', Point(43.9511, 6.3708),  radius=2000)
    ch3 = Checkpoint('B37', Point(43.9658, 6.5578), 'es',
                     (1347714900, 1347732000), radius=1500)
    ch4 = Checkpoint('g10', Point(43.9658, 6.5578), 'goal',
                     (1347714900, 1347732000), 1000)
    return [ch1, ch2, ch2_ordinal, ch3, ch4]