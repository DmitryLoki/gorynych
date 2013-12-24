'''
Functions used in other tests.
'''
from random import randint

from shapely.geometry import Point

from gorynych.common.domain.types import Checkpoint, Name
from gorynych.info.domain import contest, race, person, tracker, transport

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
    pid1 = person.PersonID()
    pid2 = person.PersonID()
    r = factory.create_race('Test Race', 'racetogoal', cont.timezone, [], [],
                timelimits=(cont.start_time, cont.end_time))
    r.paragliders['12'] = race.Paraglider(pid1, Name('Vasya', 'Hyev'),
         'RUSSIA velikaya nasha derzhava Rossia velikaya nasha strana',
         'pizdatyi glider', '12')
    r.paragliders['13'] = race.Paraglider(pid2, Name('John', 'Doe'),
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


def create_tracker():
    dev_type = 'tr203'
    dev_id = '1234567890' + str(randint(1, 100500))
    result = tracker.TrackerFactory().create_tracker(device_id=dev_id,
                                              device_type=dev_type,
                                              name='trekkie monster' + str(randint(1, 100500)))
    return result


def create_transport(transport_type):
    return transport.TransportFactory().create_transport(
        transport_type=transport_type,
                                               title='MyFeet' + str(randint(1, 100500)),
                                               description='Alive! Safe! Eagle!')


def create_person(name='John', surname='Doe',
                  country='UA', email='johndoe@example.com', id=None):
    factory = person.PersonFactory()
    pers = factory.create_person(name, surname, country, email, id)
    return pers
