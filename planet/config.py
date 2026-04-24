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

import os, sys, re, urllib.request, urllib.parse, urllib.error
from configparser import ConfigParser
from urllib.parse import urljoin

from . import output

parser = ConfigParser(interpolation=None)

planet_predefined_options = ['filters', 'excerpt', 'regexp', 'sed']
SED_FILTERS = {
    'feedburner': 'stripAd/feedburner.sed',
    'google_ad_map': 'stripAd/google_ad_map.sed',
    'yahoo': 'stripAd/yahoo.sed',
}
READING_LIST_TYPES = ('opml', 'csv', 'config')

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

    # define a list planet-level variable
    def define_planet_list(name, default=''):
        setattr(config, name, lambda : expand(get(None,name,default)))
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
    define_planet('pubsubhubbub_hub', '')
    define_planet_list('pubsubhubbub_feeds', output.RSS_OUTPUT_NAME)

    define_planet_int('new_feed_items', 0) 
    define_planet_int('feed_timeout', 20)
    define_planet_int('cache_keep_entries', 10)
    define_planet_int('items_per_page', 60)

    define_planet_list('filter_directories', 'filters')

    # section-level options still used by feeds and filters
    define_tmpl_int('activity_threshold', 0)
    define_tmpl('encoding', 'utf-8')
    define_tmpl('content_type', 'utf-8')
    define_tmpl('ignore_in_feed', '')
    define_tmpl('name_type', '')
    define_tmpl('title_type', '')
    define_tmpl('summary_type', '')
    define_tmpl('content_type', '')
    define_tmpl('future_dates', 'keep')
    define_tmpl('xml_base', '')
    define_tmpl('filter', None) 
    define_tmpl('exclude', None) 
    define_tmpl_bool('excerpt', False)
    define_tmpl('regexp', '')
    define_tmpl('sed', '')

def load(config_files):
    """ initialize and load a configuration"""
    global parser
    parser = ConfigParser(interpolation=None)
    parser.read(config_files)

    from . import config
    import planet
    from planet import opml, csv_config
    log = planet.logger
    if not log:
        log = planet.getLogger(config.log_level(),config.log_format())

    # Filter support
    dirs = config.filter_directories()
    filter_dir = os.path.join(sys.path[0],'filters')
    if filter_dir not in dirs and os.path.exists(filter_dir):
        parser.set('Planet', 'filter_directories', ' '.join(dirs+[filter_dir]))

    # Reading list support
    reading_lists = config.reading_lists()
    if reading_lists:
        if not os.path.exists(config.cache_lists_directory()):
            os.makedirs(config.cache_lists_directory())

        def data2config(data, cached_config):
            list_type = reading_list_type(list)
            if list_type == 'opml':
                opml.opml2config(data, cached_config)
            elif list_type == 'csv':
                csv_config.csv2config(data, cached_config)
            elif list_type == 'config':
                cached_config.read_file(data)
            else:
                raise ValueError("Unsupported reading list type: %s" %
                    content_type(list))

            if cached_config.sections() in [[], [list]]: 
                raise Exception

        for list in reading_lists:
            downloadReadingList(list, parser, data2config)

def downloadReadingList(list, orig_config, callback, use_cache=True, re_read=True):
    from planet import logger
    from . import config
    try:

        import urllib.request, urllib.error, urllib.parse, io
        from planet.spider import filename

        # list cache file name
        cache_filename = filename(config.cache_lists_directory(), list)

        # retrieve list options (e.g., etag, last-modified) from cache
        options = {}

        # add original options
        for key in orig_config.options(list):
            options[key] = orig_config.get(list, key)
            
        try:
            if use_cache:
                cached_config = ConfigParser(interpolation=None)
                cached_config.read(cache_filename)
                for option in cached_config.options(list):
                     options[option] = cached_config.get(list,option)
        except:
            pass

        cached_config = ConfigParser(interpolation=None)
        cached_config.add_section(list)
        for key, value in options.items():
            cached_config.set(list, key, value)

        # read list
        curdir=getattr(os.path, 'curdir', '.')
        if sys.platform.find('win') < 0:
            base = urljoin('file:', os.path.abspath(curdir))
        else:
            path = os.path.abspath(os.path.curdir)
            base = urljoin('file:///', path.replace(':','|').replace('\\','/'))

        request = urllib.request.Request(urljoin(base + '/', list))
        if "etag" in options:
            request.add_header('If-None-Match', options['etag'])
        if "last-modified" in options:
            request.add_header('If-Modified-Since',
                options['last-modified'])
        response = urllib.request.urlopen(request)
        if 'etag' in response.headers:
            cached_config.set(list, 'etag', response.headers['etag'])
        if 'last-modified' in response.headers:
            cached_config.set(list, 'last-modified',
                response.headers['last-modified'])

        # convert to config.ini
        response_data = response.read()
        if isinstance(response_data, bytes):
            response_data = response_data.decode('utf-8')
        data = io.StringIO(response_data)

        if callback: callback(data, cached_config)

        # write to cache
        if use_cache:
            cache = open(cache_filename, 'w')
            cached_config.write(cache)
            cache.close()

        # re-parse and proceed
        logger.debug("Using %s readinglist", list) 
        if re_read:
            if use_cache:  
                orig_config.read(cache_filename)
            else:
                cdata = io.StringIO()
                cached_config.write(cdata)
                cdata.seek(0)
                orig_config.read_file(cdata)
    except:
        try:
            if re_read:
                if use_cache:  
                    if not orig_config.read(cache_filename): raise Exception()
                else:
                    cdata = io.StringIO()
                    cached_config.write(cdata)
                    cdata.seek(0)
                    orig_config.read_file(cdata)
                logger.info("Using cached %s readinglist", list)
        except:
            logger.exception("Unable to read %s readinglist", list)

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

def cache_blacklist_directory():
    if parser.has_option('Planet', 'cache_blacklist_directory'):
        return os.path.join(cache_directory(),
            parser.get('Planet', 'cache_blacklist_directory'))
    else:
        return os.path.join(cache_directory(), 'blacklist')

def cache_lists_directory():
    if parser.has_option('Planet', 'cache_lists_directory'):
        return parser.get('Planet', 'cache_lists_directory')
    else:
        return os.path.join(cache_directory(), 'lists')

def feed():
    if parser.has_option('Planet', 'feed'):
        return parser.get('Planet', 'feed')
    elif link():
        return urljoin(link(), output.RSS_OUTPUT_NAME)

def feedtype():
    if parser.has_option('Planet', 'feedtype'):
        return parser.get('Planet', 'feedtype')
    elif feed() and feed().find('rss')>=0:
        return 'rss'

def subscriptions():
    """ list the feed subscriptions """
    return list(__builtins__['filter'](lambda feed: feed!='Planet' and 
        feed not in filters()+reading_lists(),
        parser.sections()))

def reading_lists():
    """ list of lists of feed subscriptions """
    result = []
    for section in parser.sections():
        if reading_list_type(section):
            result.append(section)
    return result

def reading_list_type(section):
    """Return the supported reading-list type for one config section."""
    if not parser.has_option(section, 'content_type'):
        return None
    type = parser.get(section, 'content_type')
    for supported in READING_LIST_TYPES:
        if type.find(supported) >= 0:
            return supported
    return None

def filters(section=None):
    filters = []
    if regexp(section):
        filters.append('regexp_sifter.py?require=' +
            urllib.parse.quote(regexp(section)))
    if sed(section):
        filters.append(sed_filter(section))
    if excerpt(section):
        filters.append('excerpt.py')
    return filters

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

def filter_options(section):
    """ dictionary of filter specific options"""
    return feed_options(section)

def write(file=sys.stdout):
    """ write out an updated template """
    print(parser.write(file))
