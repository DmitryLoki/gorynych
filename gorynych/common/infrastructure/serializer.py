'''
Serializers for system.
'''
import simplejson as json
from gorynych.common import exceptions

class IdentifierObjectSerializer(object):

    def __init__(self, id_class):
        self.id_class = id_class

    def to_bytes(self, value):
        return bytes(value)

    def from_bytes(self, value):
        return self.id_class.fromstring(value)


class StringSerializer(object):
    def to_bytes(self, value):
        return bytes(value)

    def from_bytes(self, value):
        return value


class GeoObjectListSerializer(object):

    def __init__(self, factory):
        self.factory = factory

    def to_bytes(self, values):
        result = '[' + bytes(json.dumps(values[0].__geo_interface__))
        for value in values[1:]:
            result = ','.join((result,
                               bytes(json.dumps(value.__geo_interface__))))
        return bytes(','.join((result, ']')))

    def from_bytes(self, byte_value):
        values = json.loads(byte_value)
        if not isinstance(values, list):
            raise exceptions.DeserializationError("I need a list.")
        result = []
        for item in values:
            result.append(self.factory(item))
        return result
