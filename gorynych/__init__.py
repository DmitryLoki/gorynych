'''
Gorynych is a GPS-tracking and analyzing backend for airtribune.com.
'''
import yaml
import os

__version__ = 0.1
config_file = 'config.yaml'

# Set GOR_ENV to develop if version is odd and not environment variable is set.
if 10 * __version__ % 2:
    if not os.getenv('GOR_ENV', None):
        os.environ['GOR_ENV'] = 'develop'

path_join = os.path.join(os.path.dirname(__file__), config_file)
if os.path.isfile(path_join):
    with open(path_join, 'r') as f:
        configs = yaml.safe_load(f)

        OPTS = configs['default']
        env = os.getenv('GOR_ENV', 'default').lower()
        # Update default values with environments
        OPTS.update(configs.get(env, ''))
