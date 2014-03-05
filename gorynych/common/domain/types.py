'''
Common types.
'''
import simplejson as json

from shapely.geometry import shape
from gorynych.common.domain.model import ValueObject
from gorynych.common.domain.services import point_dist_calculator


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
            raise ValueError("Country can't be set without code.")

    def code(self):
        return self._code


class Address(ValueObject):

    def __init__(self, place, country, coordinates):
        self._place = place.strip().capitalize()
        if not isinstance(country, Country):
            country = Country(country)
        self._country = country
        if isinstance(coordinates, str):
            coordinates = coordinates.split(',')
        self.lat = float(coordinates[0])
        self.lon = float(coordinates[1])
        if not (-90 < self.lat < 90 and -180 <= self.lon <= 180):
            raise ValueError("Coordinates not in their range or format.")

    @property
    def country(self):
        return self._country.code()

    @property
    def coordinates(self):
        return self.lat, self.lon

    @property
    def place(self):
        return self._place


class Checkpoint(ValueObject):
    '''
    Checkpoint object is a GeoJSON Feature. It exposes python geo interface as
    described here: L{https://gist.github.com/sgillies/2217756}
    '''
    def __init__(self, name, geometry, ch_type=None, times=None,
            radius=None, checked_on='enter'):
        if ch_type:
            self.type = ch_type.strip().lower()
        else:
            self.type = 'ordinal'
        self.name = name.strip().upper()
        if isinstance(geometry, dict):
            self.geometry = shape(geometry)
        else:
            self.geometry = geometry
        if self.geometry.geom_type == 'Point':
            try:
                self.radius = int(radius)
            except TypeError:
                raise ValueError("Bad radius for cylinder checkpoint.")
        if times:
            self.open_time, self.close_time = times
        else:
            self.open_time, self.close_time = None, None
        if self.open_time and self.close_time:
            assert int(self.close_time) > int(self.open_time), \
                "Checkpoint close_time must be after open_time."
        if not checked_on == 'enter':
            checked_on = 'exit'
        self.checked_on = checked_on
        # Distance to something.
        self.distance = 0
        # XXX Optimum js-distance porn
        self.aPoint = None

    @property
    def lat(self):
        # XXX: remove lat/lon properties from Checkpoint.
        return self.__geo_interface__['geometry']['coordinates'][1]

    @property
    def lon(self):
        # XXX: it's wrong interface.
        return self.__geo_interface__['geometry']['coordinates'][0]

    def distance_to(self, point):
        '''
        Calculate distance from point to checkpoint.
        @param point:
        @type point: C{tuple} or C{Checkpoint}
        @return:
        @rtype: C{float}
        '''
        if isinstance(point, tuple):
            lat, lon = float(point[0]), float(point[1])
        elif isinstance(point, Checkpoint):
            lat = point.__geo_interface__['geometry']['coordinates'][0]
            lon = point.__geo_interface__['geometry']['coordinates'][1]
        else:
            raise TypeError("Unknown type %s" % type(point))
        _lat = self.__geo_interface__['geometry']['coordinates'][0]
        _lon = self.__geo_interface__['geometry']['coordinates'][1]
        return point_dist_calculator(lat, lon, _lat, _lon)

    @property
    def __geo_interface__(self):
        '''
        Exposes python geo interface as
        described here: L{https://gist.github.com/sgillies/2217756}
        '''
        result = dict(type='Feature')
        result['properties'] = {}
        result['properties']['checkpoint_type'] = self.type
        result['properties']['name'] = self.name
        if hasattr(self, 'radius'):
            result['properties']['radius'] = self.radius
        result['properties']['open_time'] = self.open_time
        result['properties']['close_time'] = self.close_time
        result['properties']['checked_on'] = self.checked_on
        result['geometry'] = self.geometry.__geo_interface__
        return result

    def __eq__(self, other):
        return self.__geo_interface__ == other.__geo_interface__

    def __ne__(self, other):
        return self.__geo_interface__ != other.__geo_interface__

    @staticmethod
    def from_geojson(value):
        '''
        Create Checkpoints intsance from GeoJSON string or dict.
        @param value: string or dict which looks like correct GeoJSON thing:
        http://geojson.org/geojson-spec.html#examples
        '''
        if isinstance(value, str):
            value = json.loads(value)
        return checkpoint_from_geojson(value)

    def __str__(self):
        return bytes(json.dumps(self.__geo_interface__))

def checkpoint_from_geojson(geodict):
    '''
    Create L{Checkpoint} instance from geojson-like dictionary.
    @param geodict: dictionary which json representation is a correct
    GeoJSON string.
    @type geodict: C{dict}
    @return: L{Checkpoint} instance
    @rtype: L{Checkpoint}
    '''
    assert isinstance(geodict, dict), "I need a dict for checkpoint creation" \
                                      " but got %s" % type(geodict)
    # Checkpoint is a Feature so it must have 'geometry' and 'properties' keys.
    name = geodict['properties'].get('name')
    ch_type = geodict['properties'].get('checkpoint_type', 'ordinal')
    open_time = geodict['properties'].get('open_time')
    close_time = geodict['properties'].get('close_time')
    radius = geodict['properties'].get('radius')
    geometry = geodict['geometry']
    checked_on = geodict['properties'].get('checked_on', 'enter')
    return Checkpoint(name, geometry, ch_type,
                      (open_time, close_time), radius, checked_on)

def checkpoint_collection_from_geojson(data):
    if not isinstance(data, dict):
        data = json.loads(data)

    result = []
    for ch in data['features']:
        result.append(checkpoint_from_geojson(ch))
    return result

def geojson_feature_collection(ch_list):
    assert isinstance(ch_list, list), "I'm waiting for list of Checkpoint."
    result = []
    for i, item in enumerate(ch_list):
        result.append(item.__geo_interface__)
    return json.dumps(dict(type='FeatureCollection',
                           features=result))
