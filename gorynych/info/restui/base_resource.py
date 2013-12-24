'''
Resources for RESTful API.
'''
import os
import re
import simplejson as json

import yaml

from twisted.web import resource, server
from twisted.internet import defer
from twisted.python import log

from gorynych.common.infrastructure.encoders import DomainJsonEncoder
from gorynych.common.exceptions import NoAggregate, DomainError

class BadParametersError(Exception):
    '''
    Raised when bad parameters has been passed to the system.
    '''

YAML_TREE_FILE = 'resources_tree.yaml'


def json_renderer(data, template_name=None):
    try:
        return json.dumps(data, cls=DomainJsonEncoder)
    except TypeError as e:
        raise TypeError('Failed to encode json response: {}'.format(e.message))


def resource_tree(filename=os.path.join(os.path.dirname(__file__),
                                YAML_TREE_FILE)):
    result = yaml.load(open(filename, 'r'))
    return result


class APIResource(resource.Resource):
    '''
    Base API resource class.
    '''
    default_content_type = 'application/json'
    renderers = {'application/json': json_renderer}
    name = 'APIResource'
    service_command = {}
    templates = {}

    def __init__(self, tree, service):
        resource.Resource.__init__(self)
        self.tree = tree
        self.service = service

    def getChild(self, path, request):
        """
        Dynamically return new child.
        @param path:
        @type path:
        @param request:
        @type request:
        @return: api resource
        @rtype: C{Resource}
        """
        if path == '':
            if self.__class__.__name__ == 'APIResource':
                # Return NoResource for / resource. Replace it with base
                # resource which will show root page.
                return resource.NoResource()
            else:
                return self
        for key in self.tree.keys():
            if re.search(key, path):
                res = getattr(self.tree[key]['package'],self.tree[key]['leaf'])
                res_tree = self.tree[key].get('tree')
                if not res_tree:
                    res.isLeaf = 1
                return res(res_tree, self.service)
        return resource.NoResource()


    def render_HEAD(self, request):
        return ''


    @defer.inlineCallbacks
    def _render_method(self, request, method_func, request_params=None):
        '''
        Other render_METHOD methods delegate their work to this method.
        Most of the work is doing here.
        @param request: request passed to resource.
        @type request: L{Request}
        @param method_func: function which handle METHOD action (create,
        change, delete etc)
        @type method_func:
        @return: deferred which wraps result or '' string.
        @rtype: C{Deferred}
        '''
        # get parameters from request
        if not request_params:
            try:
                request_params = self.parameters_from_request(request)
                #log.msg("request: %r params: %s " % (request, request_params) )
            except Exception as error:
                self._handle_error(request, 400, "Bad input parameters or URI",
                    repr(error))
                defer.returnValue('')

        # get service function which will handle request
        try:
            service_method = getattr(
                self.service, self.service_command[request.method])
        except KeyError:
            if not request.method == 'HEAD':
                allowed_methods = self.service_command.keys()
                body = 'Next methods allowed: %s ' % allowed_methods
                # TODO: according to RFC I must write Allow header.
                self._handle_error(request, 405, 'Method now allowed', body)
                # TODO: am I need this?
                # raise UnsupportedMethod(allowed_methods)
            else:
                # HEAD method must be supported accordingly to RFC2616 5.1.1
                self.render_HEAD(request)
                defer.returnValue('')
        except AttributeError as error:
            self._handle_error(request, 500, 'Attribute error', str(error))
            defer.returnValue('')

        # service will handle request
        try:
            service_result = yield service_method(request_params)
        except NoAggregate as error:
            self._handle_error(request, 404, "No such resource",
                "Aggregate wasn't found in repository %s. " % error.message)
            defer.returnValue('')
        except DomainError as error:
            self._handle_error(request, 409, "Domain Error occured",
                                repr(error))
            defer.returnValue('')
        except Exception as error:
            self._handle_error(request, 500, "Error while executing service "
                                  "command", repr(error))
            defer.returnValue('')

        # use service result as supposed
        request, body = yield method_func(service_result, request,
                                          request_params)
        if not body:
            defer.returnValue('')
        self.write_request((request, body))

    def _handle_error(self, request, response_code, error, message):
        body = dict(error = str(error), message = str(message))
        body = json.dumps(body)
        request.setResponseCode(int(response_code))
        self.write_request((request, body))

    def render_GET(self, request):
        self._render_method(request, self.resource_renderer)
        return server.NOT_DONE_YET

    def render_POST(self, request):
        self._render_method(request, self.resource_created)
        return server.NOT_DONE_YET

    def render_PUT(self, request):
        self._render_method(request, self.change_resource)
        return server.NOT_DONE_YET

    def resource_renderer(self, res, req, request_params=None):
        '''
        Receive result from Application Service and represent it as http
        entity.
        @param res: return from ApplicationService.
        @type res: list or instance of AggregateRoot subclass
        '''
        content_type = req.responseHeaders.getRawHeaders('content-type',
            'application/json')
        req.setResponseCode(200)
        # will try to translate resource object into dictionary.
        method = req.method
        try:
            resource_representation = getattr(self, '_'.join(('read',
                                      method)))(res, request_params)
        except Exception as error:
            body = "Error %r in resource reading function." % error
            return self._handle_error(req, 500, "ReadError", body), None

        try:
            tmpl = self.templates.get(method, self.name)
            body = self.renderers[content_type](resource_representation, tmpl)
        except KeyError as error:
            body = 'While rendering answer as %s. Error message is %r' % (
                content_type, error)
            return self._handle_error(req, 500, "KeyError", body), None
        return req, body

    def read(self, res):
        return res

    def resource_created(self, res, req, request_params):
        '''
        Handle situation when new resource has been created.
        @type req: L{twisted.web.server.Request}
        '''
        req, body = self.resource_renderer(res, req, request_params)
        req.setResponseCode(201)
        return req, body

    def change_resource(self, res, req, request_params):
        req, body = self.resource_renderer(res, req, request_params)
        return req, body

    def write_request(self, (req, body)):
        '''
        Receive request with body and write it back to channel.
        '''
        req.setHeader('Content-Length', bytes(len(body)))
        req.setHeader('Content-Type',
            req.responseHeaders.getRawHeaders('content-type',
                'application/json'))
        req.write(bytes(body))
        req.finish()
        return server.NOT_DONE_YET

    def parameters_from_request(self, req):
        '''
        Return parameters from request arguments and/or URL.
        @param req: request
        @type req: C{Request}
        @raise BadParametersError
        @raise: ValueError("Bad JSON received") on PUT request with bad json.
        '''
        # Mapping between uri path and parameters keys because I don't want
        # to se in result {'contest': some_id} but want to see
        # {'contest_id': some_id}.
        maps = dict(contest='contest_id',
                    person='person_id',
                    race='race_id',
                    paraglider='person_id',
                    group='group_id',
                    tracker='tracker_id',
                    transport='transport_id')

        result = dict()
        if req.method in ["PUT", "POST"]:
            content = req.content.read()
            try:
                args = json.loads(content)
            except ValueError as error:
                raise ValueError("Bad JSON: %r " % error)
        else:
            args = req.args
            # If args[key] list has only one value make args[key] just a value
            # not a list.
            for key in args.keys():
                if len(args[key]) == 1:
                    args[key] = args[key][0]

        result = self._get_args(args)

        def insert(key, value):
            '''
            Insert only unexistent or unequal to existent values for key.
            '''
            key = maps.get(key, key)
            if result.has_key(key) and result[key] != value:
                raise BadParametersError("Two different values for one parameter.")
            else:
                result[key] = value
        # We already have arguments in args so we don't need them in uri.
        path = req.uri.split('?')[0].split('/')
        # Remove '' elements from the path list.
        try:
            while True:
                index = path.index('')
                path.pop(index)
        except ValueError:
            pass
        # Create parameters from path this way: path/id = {'path':'id'}.
        for index, item in enumerate(path):
            if index % 2:
                insert(path[index - 1], path[index])

        return result

    def _get_args(self, args):
        assert isinstance(args, dict), "Wrong args has been passed."
        return args
