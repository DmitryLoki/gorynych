'''
Gorynych is a GPS-tracking and analyzing backend for airtribune.com.
'''
import yaml
import os
from twisted.python import usage

__version__ = 0.1
# Set GOR_ENV to develop if version is odd and not environment variable is set.
if 10 * __version__ % 2:
    if not os.getenv('GOR_ENV', None):
        os.environ['GOR_ENV'] = 'develop'

config = os.path.join(os.path.dirname(__file__), 'config.yaml')
env = os.getenv('GOR_ENV', 'default').lower()

def get_opts(env, filename=None):
    if not filename:
        filename = config
    if os.path.isfile(filename):
        with open(filename, 'r') as f:
            configs = yaml.safe_load(f)

            result = configs['default']
            # Update default values with environments
            result.update(configs.get(env, ''))
        return result

OPTS = get_opts(env)


class BaseOptions(usage.Options):
    optParameters = [
        ['environment', 'e', 'develop'],
        ['config', 'c', None],
        ['poolthreads', 'pt', 5, None, int],
        ['workdir', '', './'],
        ['apiurl', 'url', 'http://api.airtribune.com/']
    ]

    def postOptions(self):
        o = get_opts(self['environment'], self['config'])
        self['dbhost'] = o['db']['host']
        self['dbname'] = o['db']['database']
        self['dbuser'] = o['db']['user']
        self['dbpassword'] = o['db']['password']

# OPTS['apiurl'] = 'http://api.airtribune.com/v' + str(__version__)
OPTS['apiurl'] = 'http://localhost:8085'
OPTS['workdir'] = './'