'''
Test base resources and functions for CoreAPI.
'''
import unittest
import mock

from twisted.web.test.requesthelper import DummyChannel
from twisted.web.server import Request
from twisted.web.resource import NoResource
from twisted.python.failure import Failure

from gorynych.info.restui.resources import (APIResource,
     BadParametersError, json_renderer,
    resource_tree)

class SomeResource(APIResource):
    pass


class SimpleAPIResource(APIResource):
    name = 'SimpleAPIResource'
    service_command = {'GET': 'get_the_thing', 'POST': 'post_the_thing',
                       'PUT': 'put_the_thing'}
    allowedMethods = ["GET"]
    renderers = {'application/json': lambda x, y: '::'.join((x, y))}


class SimpleService(object):
    def get_the_thing(self, thing):
        return 'The thing is %r' % thing

    def post_the_thing(self, thing):
        return 'The thing is %r' % thing

    def put_the_thing(self, thing):
        return 'The thing is %r' % thing


class APIResourceTest(unittest.TestCase):
    def setUp(self):
        self.tree_ = {
            '\w+-\w+-3\w+': {'leaf': 'SimpleAPIResource',
                             'package': __import__(
                         'test_resources',
                                 globals={"__name__": __name__}),
                             'tree': {}},
            'race': {'leaf': 'SomeResource',
                     'package': __import__('test_resources',
                     globals={"__name__": __name__}),
                     'tree': 1}, }
        self.api_resource = APIResource(self.tree_, 'service')


    def test_init(self):
        self.assertEqual(self.api_resource.isLeaf, 0)
        self.assertEqual(self.api_resource.service, 'service')
        self.assertEqual(self.api_resource.default_content_type,
            'application/json')

    def test_get_child(self):
        self.assertIsInstance(self.api_resource.getChild('', 1), NoResource)

        some_result = self.api_resource.getChild('race', 'hello')
        self.assertIsInstance(some_result, SomeResource)
        self.assertEqual(some_result.tree, 1)
        self.assertEqual(some_result.service, 'service')

        self.assertIsInstance(some_result.getChild('', 1), SomeResource)

    def test_regexp_child(self):
        self.assertIsInstance(self.api_resource.getChild('axe2-fsb3-32a', 1),
            SimpleAPIResource)
        self.assertIsInstance(self.api_resource.getChild('axe2-fsb3-42a', 1),
            NoResource)

    def test_handle_error_in_service(self):
        import json
        request = Request(DummyChannel(), 1)
        request.gotLength(0)
        req, msg = self.api_resource.handle_error_in_service(Failure(KeyError
            ("foo")), request)
        self.assertIsInstance(msg, str)
        msg = json.loads(msg)
        self.assertEqual(msg['message'], u"'foo'")
        self.assertEqual(msg['error'], "KeyError")
        self.assertEqual(req.code, 400)
        self.assertEqual(req.responseHeaders.getRawHeaders('content-type'),
                        ['application/json'])


class APIResourceMethodTest(unittest.TestCase):

    def setUp(self):
        self.api = SimpleAPIResource('hh', SimpleService())

    def tearDown(self):
        del self.api

    def _get_req(self):
        d = DummyChannel()
        d.site.resource.putChild('simple', self.api)
        req = Request(d, 1)
        req.gotLength(0)
        return req

    def test_resource_renderer(self):
        req = Request(DummyChannel(), 1)
        result, body = self.api.resource_renderer('res', req)
        self.assertEqual(result.code, 200)
        self.assertEqual(body, 'res::SimpleAPIResource')
        self.assertEqual(result.responseHeaders.getRawHeaders
            ('content-type')[0], 'application/json')
        self.assertEqual(result.responseHeaders.getRawHeaders
            ('content-length')[0], '22')

    def test_good_get(self):
        req = self._get_req()
        req.requestReceived('GET', '/simple', 'HTTP/1.1')
        self.assertEqual(req.transport.getvalue().splitlines()[-1],
            'The thing is {}::SimpleAPIResource')

    def test_good_post(self):
        req = self._get_req()
        req.requestReceived('POST', '/simple', 'HTTP/1.1')
        self.assertEqual(req.code, 201)
        self.assertEqual(req.transport.getvalue().splitlines()[-1],
            'The thing is {}::SimpleAPIResource')

    def test_good_put(self):
        req = self._get_req()
        req.requestReceived('PUT', '/simple', 'HTTP/1.1')
        self.assertEqual(req.code, 200)
        self.assertEqual(req.transport.getvalue().splitlines()[-1],
            'The thing is {}::SimpleAPIResource')


class RequestHandlingTest(unittest.TestCase):
    def setUp(self):
        self.api = SimpleAPIResource('hh', SimpleService())
        self.req = mock.Mock()

    def tearDown(self):
        del self.api

    def test_parameters_from_url(self):
        self.req.uri = '/contest/1234/race/12'
        self.req.args = {}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
                {'contest': '1234', 'race': '12'})

    def test_url_end_with_collection(self):
        self.req.uri = 'contest/1234/race/12/paragliders'
        self.req.args = {}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
                {'contest': '1234', 'race': '12'})

    def test_slash_skipping(self):
        self.req.uri = '//contest/1234//race/12/'
        self.req.args = {}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
                {'contest': '1234', 'race': '12'})

    def test_parameters_from_args_and_url(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.args = {'c': ['ru', 'de'], 'id': ['1']}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
            {'contest': '1234', 'race': '12', 'c':['ru', 'de'], 'id': '1'})


    def test_duplicated_parameters_from_args_and_url(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.args = {'c': ['ru', 'de'], 'id': ['1'], 'race': ['12']}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
            {'contest': '1234', 'race': '12', 'c':['ru', 'de'], 'id': '1'})

    def test_bad_duplicated_parameters_from_args_and_url(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.args = {'c': ['ru', 'de'], 'id': ['1'], 'race': ['13']}
        self.assertRaises(BadParametersError,
            self.api.parameters_from_request, self.req)


class JsonRendererTest(unittest.TestCase):
    def setUp(self):
        from string import Template
        self.template = {'contest': Template(
            '{"id": "$contest_id", "name": "$contest_name"}')}

    def test_base_rendering(self):
        self.assertEqual(json_renderer({'contest_id': 'hello',
                        'contest_name': 'greeter'}, 'contest', self.template),
            '{"id": "hello", "name": "greeter"}')
        self.assertRaises(TypeError, json_renderer, 1, 'contest')
        self.assertRaises(ValueError, json_renderer, dict(), 'higs')

    def test_list_rendering(self):
        import json
        test_list = [{'contest_id': 1, 'contest_name': 'one'},
                {'contest_id': '2', 'contest_name': 'two'}]
        result = json.loads(json_renderer(test_list, 'contest',
            self.template))
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[1]['id'], '2')

    def test_real_person_rendering(self):
        result = json_renderer({'person_id': '1', 'person_name': 'John'},
            'person_collection')
        self.assertEqual(result, '{"id": "1", "name": "John"}')


class YAMLTreeGenerationTest(unittest.TestCase):

    def test(self):
        tree = resource_tree()
        self.assertIsInstance(tree, dict)
        self.assertTrue(tree.has_key('contest'))
        self.assertTrue(tree.has_key('person'))
        ps = getattr(tree['person']['package'], tree['person']['leaf'])
        self.assertEqual(ps.__name__, 'PersonResourceCollection')


if __name__ == '__main__':
    unittest.main()
