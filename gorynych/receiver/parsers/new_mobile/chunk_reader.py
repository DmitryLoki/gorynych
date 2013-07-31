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
        self.format = ['lat', 'lon', 'ts', 'alt']
        # if self.pathChunk.HasField('index'):
        #     self.index = self.chunk.index
        # else:
        #     self.index=None

    def _format(self, *args):
        return dict(zip(self.format, args))

    def _get_base_point(self):
        self.base_lat = getattr(self.chunk, BasePointProto.LAT)
        self.base_lon = getattr(self.chunk, BasePointProto.LON)
        self.base_ts = getattr(self.chunk, BasePointProto.TS)
        assert self.base_lat is not None and \
            self.base_lon is not None and \
            self.base_ts is not None, 'Invalid chunk: base point missing'

        if getattr(self.chunk, BasePointProto.ALT):
            self.base_alt = getattr(self.chunk, BasePointProto.ALT)
        else:
            self.base_alt = 0
        return self.base_lat, self.base_lon, self.base_ts, self.base_alt

    def unpack(self):
        angle_divisor = getattr(self.chunk, BasePointProto.ANGLE_DIV)
        timedelta = getattr(self.chunk, BasePointProto.TIMEDELTA)

        assert angle_divisor > 0, 'Angle_div must be positive'
        assert timedelta > 0, 'Timedelta must be positive'

        angle_divisor = float(2 ** angle_divisor)

        # base point time
        lat, lon, ts, alt = self._get_base_point()
        yield self._format(lat, lon, ts, alt)

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
                        elif field == getattr(point, PointProto.LON):
                            lon = self.base_lon + \
                                point.packed[i] / angle_divisor
                        elif field == getattr(point, PointProto.ALT):
                            alt = self.base_alt + point.packed[i]
                        i += 1
                ts += timedelta

            yield self._format(lat, lon, ts, alt)

    def make_response(self):
        conf = pathchunk_pb2.PathCunkConf()
        conf.last_index = self.chunk.index
        return conf.SerializeToString()
