'''
Test base resources and functions for CoreAPI.
'''
from io import BytesIO
from twisted.internet.address import IPv4Address
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import ISSLTransport
from twisted.trial import unittest
import mock
from twisted.web.http_headers import Headers

from twisted.web.server import Request, Site, Session, NOT_DONE_YET
from twisted.web.resource import NoResource, Resource
from zope.interface import implementer

from gorynych.info.restui.resources import (APIResource,
     BadParametersError, json_renderer,
    resource_tree)
from gorynych.common.exceptions import NoAggregate

class SomeResource(APIResource):
    pass


class DummyChannel:
    class TCP:
        port = 80
        disconnected = False

        def __init__(self):
            self.written = BytesIO()
            self.producers = []

        def getPeer(self):
            return IPv4Address("TCP", '192.168.1.1', 12344)

        def write(self, data):
            if not isinstance(data, bytes):
                raise TypeError("Can only write bytes to a transport, not %r" % (data,))
            self.written.write(data)

        def writeSequence(self, iovec):
            for data in iovec:
                self.write(data)

        def getHost(self):
            return IPv4Address("TCP", '10.0.0.1', self.port)

        def registerProducer(self, producer, streaming):
            self.producers.append((producer, streaming))

        def loseConnection(self):
            self.disconnected = True


    @implementer(ISSLTransport)
    class SSL(TCP):
        pass

    site = Site(Resource())

    def __init__(self):
        self.transport = self.TCP()


    def requestDone(self, request):
        pass


class DummyRequest(object):
    """
    Represents a dummy or fake request.

    @ivar _finishedDeferreds: C{None} or a C{list} of L{Deferreds} which will
        be called back with C{None} when C{finish} is called or which will be
        errbacked if C{processingFailed} is called.

    @type headers: C{dict}
    @ivar headers: A mapping of header name to header value for all request
        headers.

    @type outgoingHeaders: C{dict}
    @ivar outgoingHeaders: A mapping of header name to header value for all
        response headers.

    @type responseCode: C{int}
    @ivar responseCode: The response code which was passed to
        C{setResponseCode}.

    @type written: C{list} of C{bytes}
    @ivar written: The bytes which have been written to the request.
    """
    uri = b'http://dummy/'
    method = b'GET'
    client = None

    def registerProducer(self, prod,s):
        self.go = 1
        while self.go:
            prod.resumeProducing()

    def unregisterProducer(self):
        self.go = 0


    def __init__(self, postpath, session=None):
        self.sitepath = []
        self.written = []
        self.finished = 0
        self.postpath = postpath
        self.prepath = []
        self.session = None
        self.protoSession = session or Session(0, self)
        self.args = {}
        self.outgoingHeaders = {}
        self.responseHeaders = Headers()
        self.responseCode = None
        self.headers = {}
        self._finishedDeferreds = []


    def getHeader(self, name):
        """
        Retrieve the value of a request header.

        @type name: C{bytes}
        @param name: The name of the request header for which to retrieve the
            value.  Header names are compared case-insensitively.

        @rtype: C{bytes} or L{NoneType}
        @return: The value of the specified request header.
        """
        return self.headers.get(name.lower(), None)


    def setHeader(self, name, value):
        """TODO: make this assert on write() if the header is content-length
        """
        self.outgoingHeaders[name.lower()] = value

    def getSession(self):
        if self.session:
            return self.session
        assert not self.written, "Session cannot be requested after data has been written."
        self.session = self.protoSession
        return self.session


    def render(self, resource):
        """
        Render the given resource as a response to this request.

        This implementation only handles a few of the most common behaviors of
        resources.  It can handle a render method that returns a string or
        C{NOT_DONE_YET}.  It doesn't know anything about the semantics of
        request methods (eg HEAD) nor how to set any particular headers.
        Basically, it's largely broken, but sufficient for some tests at least.
        It should B{not} be expanded to do all the same stuff L{Request} does.
        Instead, L{DummyRequest} should be phased out and L{Request} (or some
        other real code factored in a different way) used.
        """
        result = resource.render(self)
        if result is NOT_DONE_YET:
            return
        self.write(result)
        self.finish()


    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("write() only accepts bytes")
        self.written.append(data)

    def notifyFinish(self):
        """
        Return a L{Deferred} which is called back with C{None} when the request
        is finished.  This will probably only work if you haven't called
        C{finish} yet.
        """
        finished = Deferred()
        self._finishedDeferreds.append(finished)
        return finished


    def finish(self):
        """
        Record that the request is finished and callback and L{Deferred}s
        waiting for notification of this.
        """
        self.finished = self.finished + 1
        if self._finishedDeferreds is not None:
            observers = self._finishedDeferreds
            self._finishedDeferreds = None
            for obs in observers:
                obs.callback(None)


    def processingFailed(self, reason):
        """
        Errback and L{Deferreds} waiting for finish notification.
        """
        if self._finishedDeferreds is not None:
            observers = self._finishedDeferreds
            self._finishedDeferreds = None
            for obs in observers:
                obs.errback(reason)


    def addArg(self, name, value):
        self.args[name] = [value]


    def setResponseCode(self, code, message=None):
        """
        Set the HTTP status response code, but takes care that this is called
        before any data is written.
        """
        assert not self.written, "Response code cannot be set after data has been written: %s." % "@@@@".join(self.written)
        self.responseCode = code
        self.responseMessage = message


    def setLastModified(self, when):
        assert not self.written, "Last-Modified cannot be set after data has been written: %s." % "@@@@".join(self.written)


    def setETag(self, tag):
        assert not self.written, "ETag cannot be set after data has been written: %s." % "@@@@".join(self.written)


    def getClientIP(self):
        """
        Return the IPv4 address of the client which made this request, if there
        is one, otherwise C{None}.
        """
        if isinstance(self.client, IPv4Address):
            return self.client.host
        return None


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

    def test_handle_error(self):
        import json
        request = Request(DummyChannel(), 1)
        request.gotLength(0)
        self.api_resource.write_request = mock.Mock()
        result = self.api_resource._handle_error(request,
            500, 'Error', 'Big mistake')
        request.setResponseCode(500)
        body = json.dumps({'error': 'Error', 'message': 'Big mistake'})
        self.api_resource.write_request.assert_called_with((request, body))

    def test_write_unicode(self):
        request = Request(DummyChannel(), 1)
        request.gotLength(0)
        self.assertTrue(self.api_resource.write_request((request, u'hello')))


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

    def test_error_in_read_function(self):
        req = Request(DummyChannel(), 1)
        req.setResponseCode(200)
        def error_function(a):
            raise Exception("boom")
        self.api.read = error_function
        self.api._handle_error = mock.Mock()
        result, body = self.api.resource_renderer('res', req)
        self.api._handle_error.assert_called_with(req, 500, "ReadError",
            "Error %r in aggregate reading function." % Exception('boom'))


    def test_good_get(self):
        req = self._get_req()
        req.requestReceived('GET', '/simple', 'HTTP/1.1')
        self.assertEqual(req.transport.getvalue().splitlines()[-1],
            'The thing is {}::SimpleAPIResource')

    def test_good_post(self):
        req = self._get_req()
        req.args = {'arg1': 'value1'}
        req.requestReceived('POST', '/simple', 'HTTP/1.1')
        self.assertEqual(req.code, 201)
        self.assertEqual(req.transport.getvalue().splitlines()[-1],
            'The thing is {}::SimpleAPIResource')

    def test_good_put(self):
        self.skipTest("I'm not sure what I want here.")
        req = self._get_req()
        req.requestReceived('PUT', '/simple', 'HTTP/1.1')
        self.assertEqual(req.code, 200)
        self.assertEqual(req.transport.getvalue().splitlines()[-1],
            'The thing is {}::SimpleAPIResource')


class RenderMethodTest(unittest.TestCase):
    def test_error_in_parameters(self):
        req = DummyRequest([])
        service = SimpleService()
        ar = APIResource('hh', service)

        def error_in_parameters_handling(req):
            raise ValueError("Boom")
        ar.parameters_from_request = error_in_parameters_handling

        req.setResponseCode = mock.Mock()
        result = ar._render_method(req, 1)
        req.setResponseCode.assert_called_with(400)

    def test_no_such_aggregate(self):
        req = DummyRequest([])
        service = SimpleService()
        ar = APIResource('hh', service)
        ar.service_command['GET'] = 'get_the_thing'
        def no_aggregate(a):
            raise NoAggregate("hoho")
        req.setResponseCode = mock.Mock()
        service.get_the_thing = no_aggregate
        result = ar._render_method(req, 1)
        req.setResponseCode.assert_called_with(404)


class ParametersFromRequestTest(unittest.TestCase):
    def setUp(self):
        self.api = SimpleAPIResource('hh', SimpleService())
        self.req = mock.Mock()

    def tearDown(self):
        del self.api

    def test_parameters_from_url(self):
        self.req.uri = '/contest/1234/race/12'
        self.req.args = {}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
                {'contest_id': '1234', 'race_id': '12'})

    def test_url_end_with_collection(self):
        self.req.uri = 'contest/1234/race/12/paragliders'
        self.req.args = {}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
                {'contest_id': '1234', 'race_id': '12'})

    def test_slash_skipping(self):
        self.req.uri = '//contest/1234//race/12/'
        self.req.args = {}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
                {'contest_id': '1234', 'race_id': '12'})

    def test_parameters_from_args_and_url(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.args = {'c': ['ru', 'de'], 'id': ['1']}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
            {'contest_id': '1234', 'race_id': '12', 'c':['ru', 'de'], 'id': '1'})


    def test_duplicated_parameters_from_args_and_url(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.args = {'c': ['ru', 'de'], 'id': ['1'], 'race_id': ['12']}
        self.assertDictEqual(self.api.parameters_from_request(self.req),
            {'contest_id': '1234', 'race_id': '12', 'c':['ru', 'de'], 'id': '1'})

    def test_bad_duplicated_parameters_from_args_and_url(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.args = {'c': ['ru', 'de'], 'id': ['1'], 'race_id': ['13']}
        self.assertRaises(BadParametersError,
            self.api.parameters_from_request, self.req)

    def test_put_parameters(self):
        self.req.uri = '/contest/1234/race/12/paraglider/'
        self.req.content.read = mock.Mock()
        self.req.content.read.return_value = '{"a":1, "b":"2"}'
        self.req.method = "PUT"
        self.assertDictEqual(self.api.parameters_from_request(self.req),
        {'contest_id': '1234', 'race_id': '12', 'a':1, 'b':'2'})


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
        self.assertRaises(ValueError, json_renderer, {'a':1}, 'higs')

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

    def test_render_empty_response(self):
        self.assertEqual(json_renderer(None, 'haha'), '{}')


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
