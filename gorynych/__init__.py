'''
Gorynych is a GPS-tracking and analyzing backend for airtribune.com.
'''
import yaml
import os
from twisted.python import usage

__version__ = '0.2'

BASEDIR = os.path.dirname(__file__)

def get_opts_from_config(env, filename):
    if not filename.startswith('/'):
        filename = os.path.join(BASEDIR, filename)
    if os.path.isfile(filename):
        with open(filename, 'r') as f:
            configs = yaml.safe_load(f)

            result = configs['default']
            # Update default values with environments
            result.update(configs.get(env, ''))
        return result


class BaseOptions(usage.Options):
    optParameters = [
        ['environment', 'e', 'develop'],
        ['config', 'c', 'config.yaml'],
        ['poolthreads', 'pt', 5, None, int],
        ['workdir', '', './'],
        ['apiurl', 'url', 'http://api.airtribune.com']
    ]

    def postOptions(self):
        o = get_opts_from_config(self['environment'], self['config'])
        if o:
            for key in o:
                self[key] = o[key]

    def parseArgs(self, *args):
        pass


OPTS = BaseOptions()
OPTS.parseOptions([])
