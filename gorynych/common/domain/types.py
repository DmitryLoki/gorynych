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
            self.firstname = name
        else:
            raise ValueError("Firstname must be set.")

        if surname:
            self.lastname = surname
        else:
            raise ValueError("Lastname must be set.")

    def short(self):
        return '. '.join((self.firstname.capitalize()[0],
            self.lastname.capitalize()))

    def full(self):
        return ' '.join((self.firstname.capitalize(),
                         self.lastname.capitalize()))


class Country(ValueObject):

    def __init__(self, code=None):
        if code:
            self._code = code.upper()
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
    def __init__(self, name, geometry, times=None, ch_type=None, radius=None):
        self.type = ch_type.strip().lower()
        self.name = name.strip().upper()
        if geometry.geom_type == 'Point':
            try:
                self.radius = int(radius)
            except TypeError:
                raise ValueError("Bad radius for cylinder checkpoint.")
            self.geometry = geometry
        if times:
            self.start_time, self.end_time = times
