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

    def render_GET(self, request):
        d = defer.Deferred()
        d.addCallback(parameters_from_request)
        d.addCallbacks(getattr(self.service, self.service_command['get']))
        d.addCallbacks(self.resource_renderer, self.handle_error_in_service,
                       callbackArgs=[request], errbackArgs=[request])
        d.addCallbacks(self.write_request)
        d.callback((request.uri, request.args))
        return server.NOT_DONE_YET

    def render_POST(self, request):
        d = defer.Deferred()
        d.addCallback(parameters_from_request)
        d.addCallbacks(getattr(self.service, self.service_command['post']))
        d.addCallbacks(self.resource_created, self.handle_error_in_service,
                       callbackArgs=[request], errbackArgs=[request])
        d.addCallbacks(self.write_request)
        d.callback((request.uri, request.args))
        return server.NOT_DONE_YET

    def render_PUT(self, request):
        d = defer.Deferred()
        d.addCallback(parameters_from_request)
        d.addCallbacks(getattr(self.service, self.service_command['put']))
        d.addCallbacks(self.change_resource, self.handle_error_in_service,
                       callbackArgs=[request], errbackArgs=[request])
        d.addCallbacks(self.write_request)
        d.callback((request.uri, request.args))
        return server.NOT_DONE_YET

    def resource_renderer(self, res, req):
        '''
        Receive result from Application Service and represent it as http
        entity.
        '''
        content_type = req.responseHeaders.getRawHeaders('content-type',
            'application/json')
        req.setResponseCode(200)
        req.setHeader('Content-Type', content_type)
        resource_representation = self.read(res)
        body = self.renderers[content_type](resource_representation,
            self.name)
        req.setHeader('Content-Length', bytes(len(body)))
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
        req.write(body)
        req.finish()

    def handle_error_in_service(self, error, req):
        body = dict()
        err = error.trap(KeyError)
        if err == KeyError:
            req.setResponseCode(400)
            body['error'] = 'KeyError'

        body['message'] = error.getErrorMessage()
        content_type = req.responseHeaders.getRawHeaders('content-type',
            'application/json')
        req.setHeader('Content-Type', content_type)
        req.setHeader('Content-Length', bytes(len(body)))
        body = json.dumps(body)
        return req, body


def parameters_from_request(req):
    '''
    Return parameters from request arguments and/or URL.
    @param req: string which represent request.uri, and dict request.args
    @type req: C{tuple}
    '''
    uri, args = req
    assert isinstance(args, dict), "Wrong args has been passed."
    result = dict()
    for key in args.keys():
        if len(args[key]) == 1:
            result[key] = args[key][0]
        else:
            result[key] = args[key]
    def insert(key, value):
        '''
        Insert only unexistent or unequal to existent values for key.
        '''
        if result.has_key(key) and result[key] != value:
            raise BadParametersError("Two different values for one parameter.")
        else:
            result[key] = value
    path = uri.split('?')[0].split('/')
    # remove '' elements from list
    try:
        while True:
            index = path.index('')
            path.pop(index)
    except ValueError:
        pass
    for index, item in enumerate(path):
        if index % 2:
            insert(path[index - 1], path[index])

    return result


class ContestResourceCollection(APIResource):
    '''
    Resource /contest
    '''
    allowedMethods = ["GET", "POST"]
    service_command = dict(post='create_new_contest', get='get_contests')
    name = 'contest_collection'


class ContestResource(APIResource):
    '''
    Resource /contest/{id}
    '''
    service_command = dict(get='get_contest', put='change_contest')
    name = 'contest'


class RaceResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race
    '''
    service_command = dict(get='get_contest_races',
        post='create_new_race_for_contest')
    name = 'contest_race_collection'


class RaceResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}
    '''
    service_command = dict(get='get_race', put='change_race')
    name = 'contest_race'


class ParagliderResourceCollection(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider
    '''
    service_command = dict(post='register_paraglider_on_contest')
    name = 'get_race_paragliders'


class ParagliderResource(APIResource):
    '''
    Resource /contest/{id}/race/{id}/paraglider/{id} or
    /contest/{id}/paraglider/{id}
    '''
    service_command = dict(put='change_paraglider')
    name = 'race_paraglider'


class PersonResourceCollection(APIResource):
    '''
    /person resource
    '''
    service_command = dict(get='get_persons', post='create_new_person')
    name = 'person_collection'


class PersonResource(APIResource):
    '''
    /person/{id} resource
    '''
    isLeaf = 1
    service_command = dict(get='get_person', put='change_person')
    name = 'person'