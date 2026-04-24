xmlns = 'http://planet.intertwingly.net/'

logger = None
loggerParms = None

import os, sys, re
from . import config
config.__init__()

from configparser import ConfigParser
from urllib.parse import urljoin

def getLogger(level, format):
    """ get a logger with the specified log level """
    global logger, loggerParms
    if logger and loggerParms == (level,format): return logger

    try:
        import logging
        logging.basicConfig(format=format)
    except:
        import compat_logging as logging
        logging.basicConfig(format=format)

    logger = logging.getLogger("planet.runner")
    logger.setLevel(logging.getLevelName(level))
    try:
        logger.warning
    except:
        logger.warning = logger.warn

    loggerParms = (level,format)
    return logger

vendor_path = os.path.join(os.path.dirname(__file__), 'vendor')
if vendor_path not in sys.path:
    sys.path.append(vendor_path)

# Configure feed parser
import feedparser
feedparser.SANITIZE_HTML=1
feedparser.RESOLVE_RELATIVE_URIS=0
