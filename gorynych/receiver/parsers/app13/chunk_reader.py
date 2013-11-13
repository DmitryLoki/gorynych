# encoding: utf-8

from .pbformat import pathchunk_pb2
from .constants import BasePointProto, PointProto


class ChunkReader(object):

    """
    Takes a single chunk of a path. Each chunk consists of one
    base point and multiple deltas (with respect to the base point).

    Applies the base point to the deltas and makes 'em absolute.
    """

    def __init__(self, raw):
        self.chunk = pathchunk_pb2.PathCunk()
        self.chunk.ParseFromString(raw)
        self.format = ['lat', 'lon', 'ts', 'alt', 'h_speed', 'v_speed']
        # number of digits after decimal point for lat and lon
        self.precision = 6

    def _format(self, *args):
        return dict(zip(self.format, args))

    def _kmh2ms(self, value):
        return round((value * 1000.0) / 3600.0, 1)

    def _get_base_point(self):
        self.base_lat = getattr(self.chunk, BasePointProto.LAT)
        self.base_lon = getattr(self.chunk, BasePointProto.LON)
        self.base_ts = getattr(self.chunk, BasePointProto.TS)
        assert self.base_lat is not None and \
            self.base_lon is not None and \
            self.base_ts is not None, 'Invalid chunk: base point missing'

        self.base_alt = getattr(self.chunk, BasePointProto.ALT, 0)
        self.base_h_speed = getattr(self.chunk, BasePointProto.H_SPEED, 0)
        self.base_v_speed = self._kmh2ms(getattr(self.chunk, BasePointProto.V_SPEED, 0))

        return self.base_lat, self.base_lon, self.base_ts, self.base_alt, \
            self.base_h_speed, self.base_v_speed

    def unpack(self):
        angle_divisor = getattr(self.chunk, BasePointProto.ANGLE_DIV)
        timedelta = getattr(self.chunk, BasePointProto.TIMEDELTA)

        assert angle_divisor > 0, 'Angle_div must be positive'
        assert timedelta > 0, 'Timedelta must be positive'

        angle_divisor = float(2 ** angle_divisor)

        # base point time
        lat, lon, ts, alt, h_speed, v_speed = self._get_base_point()
        yield self._format(lat, lon, ts, alt, h_speed, v_speed)

        # unpack time!
        for point in self.chunk.point:

            if point.HasField(BasePointProto.ALT):
                self.base_alt = alt = getattr(point, BasePointProto.ALT)

            if len(point.packed) > 1:
                mask = point.packed[0]
                i = 1
                for field in xrange(point.PACKED_FIELDS_NUMBER):
                    if mask & (1 << field):
                        if field == getattr(point, PointProto.TS):
                            timedelta = point.packed[i]
                        elif field == getattr(point, PointProto.LAT):
                            lat = self.base_lat + \
                                point.packed[i] / angle_divisor
                            lat = round(lat, self.precision)
                        elif field == getattr(point, PointProto.LON):
                            lon = self.base_lon + \
                                point.packed[i] / angle_divisor
                            lon = round(lon, self.precision)
                        elif field == getattr(point, PointProto.ALT):
                            alt = self.base_alt + point.packed[i]
                        elif field == getattr(point, PointProto.H_SPEED):
                            h_speed = point.packed[i]
                        elif field == getattr(point, PointProto.V_SPEED):
                            v_speed = point.packed[i]
                            v_speed = self._kmh2ms(v_speed)
                        i += 1
                ts += timedelta

            yield self._format(lat, lon, ts, alt, h_speed, v_speed)

    def make_response(self):
        conf = pathchunk_pb2.PathCunkConf()
        conf.last_index = self.chunk.index
        return conf.SerializeToString()
