from gorynych.info.restui import resources
from gorynych.info.restui.base_resource import APIResource
from gorynych import BASEDIR

import re
import os
import json
import jsonschema


def patched_render(self, request, method_func):
    if request.method in ['PUT', 'POST']:
        subtree = self._validation.tree
        validation_path = [request.method]

        for i, item in enumerate(request.prepath):
            if item != '' and item in subtree:
                validation_path.append(item)
                if 'tree' in subtree[item]:
                    subtree = subtree[item]['tree']
                    if i == len(request.prepath) - 1:
                        validation_path.append('collection')
            elif re.match(subtree.keys()[0], item):
                next = subtree.values()[0]
                if 'tree' in next:
                    subtree = next['tree']

        try:
            params = self.parameters_from_request(request)
            self._validation.validate(params, validation_path)
            APIResource._render_method(self, request, method_func, request_params=params)
        except Exception as e:  # could be different kinds of exception
            self._handle_error(request, 400, "Bad input parameters or URI",
                               repr(e))
    else:
        APIResource._render_method(self, request, method_func)


class ValidationRule(object):
    """
    A rule produced by ApiValidator. Contains a tree, validation_method,
    provides access to the required schema and incapsulates 'validate' method.
    """
    def __init__(self, tree, validation_method):
        self.tree = tree
        self.validation_method = validation_method

    def _load_schema(self, path):

        filepath = os.path.join(BASEDIR,
                                '..',
                                'validation',
                                self.validation_method,
                                *[p for p in path[1:] if p != 'collection'])
        filepath = os.path.join(filepath, '_'.join(path).lower() + '.json')
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                schema = f.read()
            return schema

    def validate(self, params, path):
        raw_schema = self._load_schema(path)
        method = getattr(self, '_validate_' + self.validation_method)
        if not raw_schema or not method:
            # no validation supplied. shall I raise the alarm?
            pass
        else:
            method(params, raw_schema)

    def _validate_jsonschema(self, params, raw_schema):
        schema = json.loads(raw_schema)
        jsonschema.validate(params, schema)


class ApiValidator(object):
    """
    Monkey-patches API so it would call "validate" method
    on any not-GET calls against specified validation mechanism
    and return 400 Bad Request if validation is failed.
    Usage:

     * initialize it with selected validation mechanism (default is "jsonschema") and your api tree
     * call apply() to monkeypatch resources

    You must verify that "validation" folder at the root of the project
    is properly filled with validation templates.
    """

    def __init__(self, apitree, validation_method='jsonschema'):
        self.resources = []
        self.validation_method = validation_method
        self.add_tree(apitree)

    def add_tree(self, tree):
        # accepts apitree extracted from yaml config
        leaves = []

        def recurse(branch):
            if isinstance(branch, dict):
                if 'leaf' in branch:
                    leaf = getattr(resources, branch['leaf'])
                    if leaf:
                        leaves.append(leaf)
                if 'tree' in branch:
                    for k, v in branch['tree'].iteritems():
                        recurse(v)

        if 'leaf' in tree or 'tree' in tree:
            recurse(tree)
        else:
            for k, v in tree.iteritems():
                recurse(v)

        if not leaves:
            raise TypeError("No resources were found in a tree: it should contain \
                             at least one 'leaf' element")
        self.resources = leaves
        self.tree = tree

    def apply(self):
        if not self.resources:
            raise Exception('Nothing to validate: add some resources first')
        for r in self.resources:
            r._validation = ValidationRule(self.tree, self.validation_method)
            r._render_method = patched_render


