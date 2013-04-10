'''
Resources for RESTful API.
'''
import os
import re
import json
from string import Template

import yaml

from twisted.web import resource, server
from twisted.internet import defer
from twisted.web.error import UnsupportedMethod

from gorynych.common.exceptions import NoAggregate

class BadParametersError(Exception):
    '''
    Raised when bad parameters has been passed to the system.
    '''

JSON_TEMPLATES_DIR = 'json_templates'
YAML_TREE_FILE = 'resources_tree.yaml'

def load_json_templates(dir):
    result = dict()
    files_list = filter(os.path.isfile,
        map(lambda x: os.path.join(dir, x), os.listdir(dir)))
    for filename in files_list:
        # read every nonempty *.json file and put content into json_templates
        if filename.endswith('.json') and os.stat(filename).st_size > 0:
            result[os.path.basename(filename).split('.')[0]] =\
                                                Template(open(filename).read())
    return result


JSON_TEMPLATES = load_json_templates(os.path.join(os.path.dirname(__file__),
    JSON_TEMPLATES_DIR))


def json_renderer(template_values, template_name,
                  templates_dict=JSON_TEMPLATES):

    def render(value, template):
        ''' Do actual rendering. Return string.
        '''
        return template.substitute(value)

    # render empty result
    if not template_values:
        return "{}"
    # get template from a dict
    template = templates_dict.get(template_name)
    if not template:
        raise ValueError("Template with such name doesn't exist.")

    if isinstance(template_values, list):
        # Result will be json array.
        result = '[' + render(template_values[0], template)
        for value in template_values[1:]:
            json_obj = render(value, template)
            result = ','.join((result, json_obj))
        result = ''.join((result, ']'))
        return result

    elif isinstance(template_values, dict):
        return render(template_values, template)
    else:
        raise TypeError("Dictionary must be passed as container for template"
                        " values.")



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

    def __init__(self, tree, service):
        resource.Resource.__init__(self)
        self.tree = tree
        self.service = service

    def getChild(self, path, request):
        """
        Dinamically return new child.
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
                return getattr(self.tree[key]['package'],
                    self.tree[key]['leaf'])(self.tree[key]['tree'], self.service)
        return resource.NoResource()


    def render_HEAD(self, request):
        return ''


    @defer.inlineCallbacks
    def _render_method(self, request, resource_func):
        # get parameters from request
        try:
            request_params = self.parameters_from_request(request)
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
                raise UnsupportedMethod(allowed_methods)
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
        except ValueError as error:
            self._handle_error(request, 500, "Error while executing service "
                                 "command", repr(error))
            defer.returnValue('')
        except NoAggregate:
            self._handle_error(request, 404, "No such resource",
                "Aggregate wasn't found in repository.")
            defer.returnValue('')

        # use service result as supposed
        request, body = yield resource_func(service_result, request)
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

    def resource_renderer(self, res, req):
        '''
        Receive result from Application Service and represent it as http
        entity.
        '''
        content_type = req.responseHeaders.getRawHeaders('content-type',
            'application/json')
        req.setResponseCode(200)
        # will try to translate resource object into dictionary.
        try:
            resource_representation = self.read(res)
        except Exception as error:
            body = "Error %r in aggregate reading function." % error
            return self._handle_error(req, 500, "ReadError", body), None

        try:
            body = self.renderers[content_type](resource_representation,
                self.name)
        except KeyError as error:
            body = 'While rendering answer as %s. Error message is %r' % (
                content_type, error)
            return self._handle_error(req, 500, "KeyError", body), None
        return req, body

    def read(self, res):
        return res

    def resource_created(self, res, req):
        '''
        Handle situation when new resource has been created.
        @type req: L{twisted.web.server.Request}
        '''
        req, body = self.resource_renderer(res, req)
        req.setResponseCode(201)
        return req, body

    def change_resource(self, res, req):
        req, body = self.resource_renderer(res, req)
        return req, body

    def write_request(self, (req, body)):
        '''
        Receive request with body and write it back to channel.
        '''
        req.setHeader('Content-Length', bytes(len(body)))
        req.setHeader('Content-Type',
            req.responseHeaders.getRawHeaders('content-type',
                'application/json'))
        req.write(body)
        req.finish()
        return req

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
        maps = {'contest': 'contest_id', 'person': 'person_id',
                'race': 'race_id'}

        result = dict()
        if req.method == "PUT":
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


class ContestResourceCollection(APIResource):
    '''
    Resource /contest
    '''
    allowedMethods = ["GET", "POST"]
    service_command = dict(POST='create_new_contest', GET='get_contests')
    name = 'contest_collection'

    def _get_args(self, args):
        if args.has_key('hq_coords'):
            args['hq_coords'] = args['hq_coords'].split(',')
        return args


class ContestResource(APIResource):
    '''
    Resource /contest/{id}
    '''
    service_command = dict(GET='get_contest', PUT='change_contest')
    name = 'contest'


class RaceResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race
    '''
    service_command = dict(GET='get_contest_races',
        POST='create_new_race_for_contest')
    name = 'contest_race_collection'


class RaceResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}
    '''
    service_command = dict(GET='get_race', PUT='change_race')
    name = 'contest_race'


class ParagliderResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider
    '''
    service_command = dict(POST='register_paraglider_on_contest')
    name = 'get_race_paragliders'


class ParagliderResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider/{id} or
    /contest/{id}/paraglider/{id}
    '''
    service_command = dict(PUT='change_paraglider')
    name = 'race_paraglider'


class PersonResourceCollection(APIResource):
    '''
    /person resource
    '''
    service_command = dict(GET='get_persons', POST='create_new_person')
    name = 'person_collection'


class PersonResource(APIResource):
    '''
    /person/{id} resource
    '''
    isLeaf = 1
    service_command = dict(GET='get_person', PUT='change_person')
    name = 'person'