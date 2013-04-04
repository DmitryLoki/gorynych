'''
Common types.
'''
from gorynych.common.domain.model import ValueObject

class Name(ValueObject):
    '''
    A type for names.
    Usage can be found in test_types
    '''

    def __init__(self, name=None, surname=None):
        if name:
            self._name = name.strip().capitalize()
        else:
            raise ValueError("Name must be set.")

        if surname:
            self._surname = surname.strip().capitalize()
        else:
            raise ValueError("Surname must be set.")

    def short(self):
        return '. '.join((self._name.capitalize()[0],
            self._surname.capitalize()))

    def full(self):
        return ' '.join((self._name, self._surname))

    @property
    def name(self):
        return self._name

    @property
    def surname(self):
        return self._surname


class Country(ValueObject):

    def __init__(self, code=None):
        if code:
            self._code = code[:2].upper()
        else:
            raise ValueError("Country can't be set with null code.")

    def code(self):
        return self._code


class Address(ValueObject):

    def __init__(self, place, country, coordinates):
        self.place = place.strip().capitalize()
        if not isinstance(country, Country):
            country = Country(country)
        self.country = country.code()
        self.lat = float(coordinates[0])
        self.lon = float(coordinates[1])
        if not (-90 < self.lat < 90 and -180 <= self.lon <= 180):
            raise ValueError("Coordinates not in their range or format.")


class Checkpoint(ValueObject):
    def __init__(self, name, geometry, ch_type=None, times=None, radius=None):
        if ch_type:
            self.type = ch_type.strip().lower()
        else:
            self.type = 'ordinal'
        self.name = name.strip().upper()
        if geometry.geom_type == 'Point':
            try:
                self.radius = int(radius)
            except TypeError:
                raise ValueError("Bad radius for cylinder checkpoint.")
            self.geometry = geometry
        if times:
            self.start_time, self.end_time = times
        else:
            self.start_time, self.end_time = None, None

    def __eq__(self, other):
        # TODO: implement correct checkpoints comparison (it's better to do  it in ValueObject class)
        return self.type == other.type and self.name == other.name
