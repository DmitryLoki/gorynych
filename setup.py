from distutils.core import setup
import os
import gorynych

def is_package(path):
    return (
        os.path.isdir(path) and
        os.path.isfile(os.path.join(path, '__init__.py'))
        )

def refresh_plugin_cache():
    from twisted.plugin import IPlugin, getPlugins
    list(getPlugins(IPlugin))


def find_packages(path, base="" ):
    """ Find all packages in path """
    packages = {}
    for item in os.listdir(path):
        dir = os.path.join(path, item)
        if is_package(dir):
            if base:
                module_name = "%(base)s.%(item)s" % vars()
            else:
                module_name = item
            packages[module_name] = dir
            packages.update(find_packages(dir, module_name))
    return packages

packages = find_packages('.').keys()
packages.append('twisted.plugins')
print packages

setup(
    name='gorynych',
    version=gorynych.__version__,
    packages=packages,
    url='http://apidocs.devc.ru/gorynych',
    license='',
    author='Boris Tsema',
    author_email='boris@tsema.ru',
    description='Gorynych is a GPS-tracking and analyzing backend for ' \
                'airtribune.com.',
    install_requires = [
        'mock > 1.0',
        'twisted == 12.3',
        'requests',
        'pyyaml',
        'pytz',
        'txpostgres'
    ],
    include_package_data=True,
    package_data={
        'twisted': ['plugins/info_plugin.py']
    }
)

refresh_plugin_cache()
