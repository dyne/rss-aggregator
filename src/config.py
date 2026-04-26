"""
Planet Configuration

This module encapsulates all planet configuration.  This is not a generic
configuration parser, it knows everything about configuring a planet - from
the structure of the ini file, to knowledge of data types, even down to
what are the defaults.

Usage:
  import config
  config.load('config.ini')

  # planet wide configuration
  print config.name()
  print config.link()

Todo:
  * error handling (example: no planet section)
"""

import os
import re
import sys
from configparser import ConfigParser
from urllib.parse import urljoin

from . import output

parser = ConfigParser(interpolation=None)

planet_predefined_options = ['excerpt', 'regexp', 'sed', 'lemmy']
SED_FILTERS = {
    'feedburner': 'stripAd/feedburner.sed',
    'google_ad_map': 'stripAd/google_ad_map.sed',
    'yahoo': 'stripAd/yahoo.sed',
}
def __init__():
    """define the struture of an ini file"""
    from . import config

    # get an option from a section
    def get(section, option, default):
        if section and parser.has_option(section, option):
            return parser.get(section, option)
        elif parser.has_option('Planet', option):
            if option == 'log_format':
                return parser.get('Planet', option, raw=True)
            return parser.get('Planet', option)
        else:
            return default

    # expand %(var) in lists
    def expand(list):
        output = []
        wild = re.compile('^(.*)#{(\w+)}(.*)$')
        for file in list.split():
            match = wild.match(file)
            if match:
                pre,var,post = match.groups()
                for sub in subscriptions():
                    value = feed_options(sub).get(var,None)
                    if value:
                        output.append(pre+value+post)
            else:
                output.append(file)
        return output

    # define a string planet-level variable
    def define_planet(name, default):
        setattr(config, name, lambda default=default: get(None,name,default))
        planet_predefined_options.append(name)

    # define a list planet-level variable
    def define_planet_int(name, default=0):
        setattr(config, name, lambda : int(get(None,name,default)))
        planet_predefined_options.append(name)

    # define a string template-level variable
    def define_tmpl(name, default):
        setattr(config, name, lambda section, default=default:
            get(section,name,default))

    # define an int template-level variable
    def define_tmpl_int(name, default):
        setattr(config, name, lambda section, default=default:
            int(get(section,name,default)))

    # define a boolean section-level variable
    def define_tmpl_bool(name, default=False):
        def value(section, default=default):
            raw = get(section, name, default and 'true' or 'false')
            if isinstance(raw, bool):
                return raw
            return str(raw).lower() in ('1', 'true', 'yes', 'on')
        setattr(config, name, value)

    # planet wide options
    define_planet('name', "Unconfigured Planet")
    define_planet('link', '')
    define_planet('cache_directory', "cache")
    define_planet('log_level', "WARNING")
    define_planet('log_format', "%(levelname)s:%(name)s:%(message)s")
    define_planet('date_format', "%B %d, %Y %I:%M %p")
    define_planet('new_date_format', "%B %d, %Y")
    define_planet('generator', 'Venus')
    define_planet('generator_uri', 'http://intertwingly.net/code/venus/')
    define_planet('owner_name', 'Anonymous Coward')
    define_planet('owner_email', '')
    define_planet('output_dir', 'output')
    define_planet('spider_threads', 0) 

    define_planet_int('new_feed_items', 0) 
    define_planet_int('feed_timeout', 20)
    define_planet_int('cache_keep_entries', 10)
    define_planet_int('items_per_page', 60)

    # section-level options still used by feeds and filters
    define_tmpl_int('activity_threshold', 0)
    define_tmpl('encoding', 'utf-8')
    define_tmpl('filter', None) 
    define_tmpl('exclude', None) 
    define_tmpl_bool('excerpt', False)
    define_tmpl('regexp', '')
    define_tmpl('sed', '')
    define_tmpl_bool('lemmy', False)

def load(config_files):
    """ initialize and load a configuration"""
    global parser
    parser = ConfigParser(interpolation=None)
    parser.read(config_files)

    from . import config as config_module
    import src as planet
    log = planet.logger
    if not log:
        log = planet.getLogger(
            config_module.log_level(),
            config_module.log_format(),
        )

def http_cache_directory():
    if parser.has_option('Planet', 'http_cache_directory'):
        return os.path.join(cache_directory(), 
            parser.get('Planet', 'http_cache_directory'))
    else:
        return os.path.join(cache_directory(), "cache")

def cache_sources_directory():
    if parser.has_option('Planet', 'cache_sources_directory'):
        return os.path.join(cache_directory(),
            parser.get('Planet', 'cache_sources_directory'))
    else:
        return os.path.join(cache_directory(), 'sources')

def feed():
    if parser.has_option('Planet', 'feed'):
        return parser.get('Planet', 'feed')
    elif link():
        return urljoin(link(), output.RSS_OUTPUT_NAME)

def feedtype():
    if parser.has_option('Planet', 'feedtype'):
        return parser.get('Planet', 'feedtype')
    elif parser.has_option('Planet', 'feed'):
        if feed() and feed().find('rss')>=0:
            return 'rss'
    elif link():
        return 'rss'

def subscriptions():
    """ list the feed subscriptions """
    return list(__builtins__['filter'](
        lambda feed: feed != 'Planet',
        parser.sections()))

def sed_filter(section=None):
    """Return the maintained sed filter path for one section."""
    script = sed(section)
    return SED_FILTERS.get(script, '')

def planet_options():
    """ dictionary of planet wide options"""
    if not parser.has_section('Planet'):
        return {}
    return dict(map(lambda opt: (opt,
        parser.get('Planet', opt, raw=(opt=="log_format"))),
        parser.options('Planet')))

def feed_options(section):
    """ dictionary of feed specific options"""
    from . import config
    options = dict([(key,value) for key,value in planet_options().items()
        if key not in planet_predefined_options])
    if parser.has_section(section):
        options.update(dict(map(lambda opt: (opt, parser.get(section,opt)),
            parser.options(section))))
    return options

def write(file=sys.stdout):
    """ write out an updated template """
    print(parser.write(file))
