'''
Gorynych is a GPS-tracking and analyzing backend for airtribune.com.
'''
import yaml
import os

__version__ = 0.1
config_file = 'config.yaml'

path_join = os.path.join(os.path.dirname(__file__), config_file)
if os.path.isfile(path_join):
    with open(path_join, 'r') as f:
        configs = yaml.safe_load(f)

        OPTS = configs['default']
        env = os.getenv('GOR_ENV', 'default').lower()
        # Update default values with environments
        OPTS.update(configs.get(env, ''))
