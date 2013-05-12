'''
Functions used in other tests.
'''
from shapely.geometry import Point
from gorynych.common.domain.types import Checkpoint, Name
from gorynych.info.domain import contest, race
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
    factory = race.RaceFactory()
    if not cont:
        # Max_end_time - 1/1/2020
        cont = create_contest(1, 1577822400)
    pid1 = PersonID()
    pid2 = PersonID()
    r = factory.create_race('Test Race', 'racetogoal',
                (cont.start_time, cont.end_time), cont.timezone)
    r.paragliders['12'] = contest.Paraglider(pid1, Name('Vasya', 'Hyev'),
         'RUSSIA velikaya nasha derzhava Rossia velikaya nasha strana',
         'pizdatyi glider', '12')
    r.paragliders['13'] = contest.Paraglider(pid2, Name('John', 'Doe'),
        'Ya nenavizhy etot ebannyi test i mena zaeblo eto pisat',
        'hyevyi glider', '13')
    r._checkpoints = create_checkpoints()
    r._start_time = 1347711300
    r._end_time = 1347732000

    return r


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