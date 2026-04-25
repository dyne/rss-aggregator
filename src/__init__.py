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

    import logging
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
try:
    import feedparser.api
    feedparser.api.PREFERRED_XML_PARSERS = []
except Exception:
    pass

_feedparser_parse = feedparser.parse
MAX_COMPAT_XML_BYTES = 2 * 1024 * 1024

def _source_text(source):
    """Return source XML text when parse input can be inspected cheaply."""
    if isinstance(source, bytes):
        return source.decode('utf-8', 'replace')
    if isinstance(source, str):
        if os.path.exists(source):
            with open(source, encoding='utf-8', errors='replace') as handle:
                return handle.read()
        return source
    return None


def _unsafe_compat_xml(xml):
    """Return True when raw XML text is unsuitable for compatibility parsing."""
    if not xml:
        return True
    if len(xml.encode('utf-8', 'replace')) > MAX_COMPAT_XML_BYTES:
        return True
    lowered = xml.lower()
    return '<!doctype' in lowered or '<!entity' in lowered

def _gr_original_ids(source):
    """Extract Google Reader original entry ids not exposed by feedparser 6."""
    xml = _source_text(source)
    if not xml or 'original-id' not in xml or _unsafe_compat_xml(xml):
        return []
    try:
        from xml.dom import minidom
        doc = minidom.parseString(xml)
    except Exception:
        return []

    ids = []
    namespace = 'http://www.google.com/schemas/reader/atom/'
    for entry in doc.getElementsByTagName('entry'):
        id_nodes = entry.getElementsByTagName('id')
        if not id_nodes:
            ids.append(None)
            continue
        original = id_nodes[0].getAttributeNS(namespace, 'original-id') or \
            id_nodes[0].getAttribute('gr:original-id')
        ids.append(original or None)
    doc.unlink()
    return ids

def _parse(source, *args, **kwargs):
    """Parse feeds with small Venus compatibility patches."""
    original_ids = _gr_original_ids(source)
    parsed = _feedparser_parse(source, *args, **kwargs)
    for entry, original_id in zip(parsed.get('entries', []), original_ids):
        if original_id:
            entry['id'] = original_id
    return parsed

feedparser.parse = _parse

if not hasattr(feedparser, '_parse_date_iso8601'):
    def _parse_date_iso8601(value):
        """Parse the ISO-8601 dates Venus used from older feedparser."""
        import datetime
        if not value:
            return None
        value = value.replace('Z', '+00:00')
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo:
            parsed = parsed.astimezone(datetime.timezone.utc)
        return parsed.timetuple()

    feedparser._parse_date_iso8601 = _parse_date_iso8601
    feedparser._parse_date_w3dtf = _parse_date_iso8601
