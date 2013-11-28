import unittest
import simplejson as json

from shapely.geometry import Point
from gorynych.info.domain.test.helpers import create_checkpoints
from gorynych.common.domain.services import point_dist_calculator

from gorynych.common.domain import types


class TypesTest(unittest.TestCase):
    def test_name(self):
        name = types.Name('firsTname  ', '  laStname')
        self.assertEqual(name.short(), 'F. Lastname')
        self.assertEqual(name.full(), 'Firstname Lastname')
        self.assertRaises(ValueError, types.Name)
        self.assertEqual(name.name, 'Firstname')
        self.assertEqual(name.surname, 'Lastname')

    def test_country(self):
        country = types.Country('mc123')
        self.assertEqual(country.code(), 'MC')
        self.assertRaises(ValueError, types.Country)


class AddressTest(unittest.TestCase):
    def test_success_creation(self):
        addr = types.Address('  ParIs', 'Fr', (1.08812, 3))
        self.assertEqual(addr.place, 'Paris')
        self.assertEqual(addr.country, 'FR')
        self.assertAlmostEqual(addr.lat, 1.08812, 6)
        self.assertAlmostEqual(addr.lon, 3, 6)

    def test_wrong_coordinates(self):
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (270, 0))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (0, 270))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (90, 0))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (-90, 0))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (-89, 180.01))
        self.assertRaises(ValueError, types.Address, 'ss', 'de', (-89, -180.01))

    def test_coordinates(self):
        a1 = types.Address('ss', 'de', (-89.999999, -180))
        self.assertEqual(a1.coordinates, (-89.999999, -180))
        types.Address('ss', 'de', (-89.999999, 180))
        types.Address('ss', 'de', (89.999999, 180))
        types.Address('ss', 'de', (89.999999, -180))

    def test_country(self):
        a = types.Address('ss', 'de', (0, 0))
        self.assertEqual(a.country, 'DE')

    def test_place(self):
        a = types.Address('ss', 'de', (0, 0))
        self.assertEqual(a.place, 'Ss')


class CheckpointTest(unittest.TestCase):
    def test_creating(self):
        point1 = Point(42.502, 0.798)
        ch1 = types.Checkpoint(name='A01', geometry=point1, ch_type='TO', times=(2, None), radius=2,
            checked_on='exit')
        ch2 = types.Checkpoint(name='A01', geometry=Point(42.502, 0.798), times=(4, 6), radius=3)
        ch3 = types.Checkpoint(name='B02', geometry=Point(1, 2), ch_type='es',
            radius=3)
        ch4 = types.Checkpoint(name='g10',
            geometry={'type': 'Point', 'coordinates': [1, 2]}, ch_type='goal',
            radius=3, times=(None, 8))

        self.assertEqual(ch1.geometry, point1)
        self.assertEqual(ch1.radius, 2)

        self.assertEqual(ch1.checked_on, 'exit')
        self.assertEqual(ch2.checked_on, 'enter')

        self.assertEqual(ch3.type, 'es')
        self.assertEqual(ch1.type, 'to')
        self.assertEqual(ch2.type, 'ordinal')

        self.assertIsNone(ch3.open_time)
        self.assertIsNone(ch3.close_time)

        self.assertEqual(ch4.name, 'G10')
        self.assertEqual(ch2.name, 'A01')

        self.assertIsInstance(ch4.geometry, Point)
        self.assertAlmostEqual(
            ch2.__geo_interface__['geometry']['coordinates'][0], 42.502, 3)
        self.assertAlmostEqual(
            ch2.__geo_interface__['geometry']['coordinates'][1], 0.798, 3)

    def test_geo_interface(self):
        ch1 = types.Checkpoint(name='A01', geometry=Point(53, 1), ch_type='TO',
            times=(2, None), radius=2)
        expected_interface = {'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [53.0, 1.0]},
            'properties': {'radius': 2, 'name': 'A01', 'checkpoint_type': 'to',
                'open_time': 2, 'close_time': None, 'checked_on': 'enter'}}

        self.assertEqual(json.dumps(ch1.__geo_interface__), json.dumps(expected_interface))

    def test_equal(self):
        ch1 = types.Checkpoint(name='A01', geometry=Point(53, 1), ch_type='TO',
            times=(2, None), radius=2)
        ch2 = types.Checkpoint(name='A01', geometry=Point(53, 1), ch_type='TO',
            times=(2, None), radius=2)
        self.assertEqual(ch1, ch2)
        ch3 = types.Checkpoint(name='A01', geometry=Point(53, 1), ch_type='TO',
            times=(2, 3), radius=2)
        self.assertNotEqual(ch1, ch3)

    def test_checkpoint_from_geojson(self):
        point = {'geometry': {'type': 'Point', 'coordinates': [0.0, 1.0]},
            'type': 'Feature',
            'properties': {'name': "A01", 'radius': 400, 'open_time': 12345,
                'close_time': 123456}}
        ch = types.checkpoint_from_geojson(point)
        self.assertIsInstance(ch, types.Checkpoint)
        self.assertEqual(ch.type, 'ordinal')
        self.assertDictContainsSubset(point['properties'],
            ch.__geo_interface__['properties'])
        self.assertIsInstance(ch.geometry, Point)

    def test_from_geojson_staticmethod_dict(self):
        point = {'geometry': {'type': 'Point', 'coordinates': [0.0, 1.0]},
            'type': 'Feature',
            'properties': {'name': "A01", 'radius': 400, 'open_time': 12345,
                'close_time': 123456}}
        ch = types.Checkpoint.from_geojson(point)
        self.assertIsInstance(ch.geometry, Point)
        self.assertIsInstance(ch, types.Checkpoint)
        self.assertEqual(ch.type, 'ordinal')
        self.assertDictContainsSubset(point['properties'],
            ch.__geo_interface__['properties'])
        self.assertIsInstance(ch.geometry, Point)

    def test_from_geojson_staticmethod_str(self):
        point = {'geometry': {'type': 'Point', 'coordinates': [0.0, 1.0]},
            'type': 'Feature',
            'properties': {'name': "A01", 'radius': 400, 'open_time': 12345,
                'close_time': 123456}}
        ch = types.Checkpoint.from_geojson(json.dumps(point))
        self.assertIsInstance(ch.geometry, Point)
        self.assertIsInstance(ch, types.Checkpoint)
        self.assertEqual(ch.type, 'ordinal')
        self.assertDictContainsSubset(point['properties'],
            ch.__geo_interface__['properties'])
        self.assertIsInstance(ch.geometry, Point)

    def test_bad_creating(self):
        self.assertRaises(ValueError, types.Checkpoint, 'A01', Point(1, 1))
        self.assertRaises(AssertionError, types.Checkpoint, '2', Point(2, 2),
            times=(3, 1), radius=1)

    def test_str(self):
        point = {'geometry': {'type': 'Point', 'coordinates': [0.0, 1.0]},
            'type': 'Feature',
            'properties': {'name': "A01", 'radius': 400, 'open_time': 12345,
                'close_time': 123456, 'checkpoint_type': 'ordinal'}}
        ch = types.Checkpoint.from_geojson(point)
        self.assertIsInstance(str(ch), bytes)
        point['properties']['checked_on'] = 'enter'
        self.assertEqual(str(ch), json.dumps(point))

    def test_geojson_feature_collection(self):
        # TODO: rewrite it without dependencies to info and with more accuracy
        ch_list = create_checkpoints()
        res = types.geojson_feature_collection(ch_list)
        self.assertIsInstance(res, str)

    def test_distance_to(self):
        coords1 = [0.0, 1.0]
        point1 = {'geometry': {'type': 'Point', 'coordinates': coords1},
            'type': 'Feature',
            'properties': {'name': "A01", 'radius': 400, 'open_time': 12345,
                'close_time': 123456}}
        coords2 = [0.0, 2.0]
        point2 = {'geometry': {'type': 'Point', 'coordinates': coords2},
            'type': 'Feature',
            'properties': {'name': "A01", 'radius': 400, 'open_time': 12345,
                'close_time': 123456}}
        ch1 = types.Checkpoint.from_geojson(point1)
        ch2 = types.Checkpoint.from_geojson(point2)

        check_distance = point_dist_calculator(coords1[0], coords1[1],
            coords2[0], coords2[1])
        self.assertEqual(ch1.distance_to(ch2), check_distance)


class A(object):
    def __init__(self, prop1, prop2=None):
        self.prop1 = prop1
        if not prop2 is None:
            self.prop2 = prop2


class EntitiesCollectionTest(unittest.TestCase):
    def setUp(self):
        ec = types.EntitiesCollection()
        ec['1'] = A('1', '2')
        ec['2'] = A('1', '3')
        ec['3'] = A('2', '4')
        ec['4'] = A('3')
        self.e = ec

    def test_lookup_existed(self):
        res = self.e.get_properties_values('prop1')
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 4)

    def test_lookup_nonexistent_with_ignore(self):
        res = self.e.get_properties_values('prop2')
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 3)

    def test_lookup_nonexistent(self):
        self.assertRaises(AttributeError, self.e.get_properties_values,
            'prop2', ignore_absent=False)


class B(object):
    def __init__(self, dic):
        self.dic = dic

    def change_dic(self, key, value, raise_exception=False):
        with types.TransactionalDict(self.dic) as dic:
            dic[key] = value
            if raise_exception:
                self.check_len()

    def check_len(self):
        assert len(self.dic) == 1, "Initial dictionary length must be 1."


class TransactionalDictTest(unittest.TestCase):
    def test_success_in_function(self):
        dic = dict(a='b')
        with types.TransactionalDict(dic) as w:
            w['c'] = 'd'
        self.assertDictEqual(dic, dict(a='b', c='d'))

    def test_no_succes_in_function(self):
        dic = dict(a='b')
        try:
            with types.TransactionalDict(dic) as w:
                w['c'] = 'd'
                raise Exception()
        except Exception:
            pass
        self.assertDictEqual(dic, dict(a='b'))

    def test_success(self):
        b = B(dict(a='b'))
        b.change_dic('c', 'd')
        self.assertDictEqual(b.dic, dict(a='b', c='d'))

    def test_no_success(self):
        b = B(dict(a='b'))
        try:
            b.change_dic('c', 'd', raise_exception=True)
        except:
            pass
        self.assertDictEqual(b.dic, dict(a='b'))


if __name__ == '__main__':
    unittest.main()
