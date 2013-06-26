'''
Serializers for system.
'''
import simplejson as json
import cPickle
# XXX: try don't relate on info package
from gorynych.info.domain import ids
from gorynych.common import exceptions

# TODO: do it properly
class DomainIdentifierSerializer(object):

    def __init__(self, klass_name):
        if not hasattr(ids, klass_name):
            raise exceptions.DeserializationError("No ID class %s"
                                                  % klass_name)
        self.klass_name = klass_name

    def to_bytes(self, value):
        return bytes(value)

    def from_bytes(self, value):
        return getattr(ids, self.klass_name).fromstring(str(value))


class StringSerializer(object):
    def to_bytes(self, value):
        return bytes(value)

    def from_bytes(self, value):
        return value


class GeoObjectsListSerializer(object):

    def __init__(self, factory):
        self.factory = factory

    def to_bytes(self, values):
        result = '[' + bytes(json.dumps(values[0].__geo_interface__))
        for value in values[1:]:
            result = ','.join((result,
                               bytes(json.dumps(value.__geo_interface__))))
        return bytes(''.join((result, ']')))

    def from_bytes(self, byte_value):
        values = json.loads(str(byte_value))
        if not isinstance(values, list):
            raise exceptions.DeserializationError("I need a list.")
        result = []
        for item in values:
            result.append(self.factory(item))
        return result


class TupleOf(object):
    def __init__(self, serializer):
        self.serializer = serializer

    def to_bytes(self, values):
        result = '(' + self.serializer.to_bytes(values[0])
        for value in values[1:]:
            result = ','.join((result, self.serializer.to_bytes(value)))
        return bytes(''.join((result, ')')))

    def from_bytes(self, byte_value):
        byte_values = byte_value[1:-1].split(',')
        result = []
        for v in byte_values:
            result.append(self.serializer.from_bytes(v))
        return tuple(result)


class JSONSerializer(object):

    def to_bytes(self, value):
        return buffer(json.dumps(value))

    def from_bytes(self, value):
        return json.loads(str(value))


class IntSerializer(object):
    def to_bytes(self, value):
        return bytes(value)

    def from_bytes(self, value):
        return int(str(value))


class NoneSerializer(object):
    def to_bytes(self, value):
        return bytes('')
    def from_bytes(self, value):
        return None


class PickleSerializer(object):
    def to_bytes(self, value):
        return buffer(cPickle.dumps(value, -1))

    def from_bytes(self, value):
        return cPickle.loads(str(value))