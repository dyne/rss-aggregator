""" Expunge old entries from a cache of entries """
import glob, os, planet
from xml.dom import minidom
from . import config, storage
from planet import feedparser
from .spider import filename

def _source_id_from_doc(entry_doc):
    """Extract source feed id from one cached entry XML document."""
    entry_doc.normalize()
    sources = entry_doc.getElementsByTagName('source')
    if not sources:
        return None
    ids = sources[0].getElementsByTagName('id')
    if not ids or not ids[0].childNodes:
        return None
    return ids[0].childNodes[0].nodeValue

def expungeCache():
    """ Expunge old entries from a cache of entries """
    log = planet.logger

    log.info("Determining feed subscriptions")
    entry_count = {}
    sources = config.cache_sources_directory()
    for sub in config.subscriptions():
        data=feedparser.parse(filename(sources,sub))
        if 'id' not in data.feed: continue
        if 'cache_keep_entries' in config.feed_options(sub):
            entry_count[data.feed.id] = int(config.feed_options(sub)['cache_keep_entries'])
        else:
            entry_count[data.feed.id] = config.cache_keep_entries()

    log.info("Listing cached entries")
    cache = config.cache_directory()
    sqlite_entries = storage.list_entries_by_recency()
    if sqlite_entries:
        for entry_key, _entry_id, feed_id, _updated_ts, entry_xml, _blacklisted in sqlite_entries:
            source_id = feed_id
            if not source_id:
                try:
                    source_id = _source_id_from_doc(minidom.parseString(entry_xml))
                except:
                    source_id = None

            if source_id in entry_count:
                entry_count[source_id] = entry_count[source_id] - 1
                if entry_count[source_id] >= 0:
                    continue
                log.debug("Removing %s, maximum reached for %s", entry_key, source_id)
            else:
                log.debug("Removing %s, not subscribed to %s", entry_key, source_id)

            storage.delete_entry(entry_key)
            file = os.path.join(cache, entry_key)
            if os.path.exists(file):
                os.unlink(file)
        return

    dir=[(os.stat(file).st_mtime,file) for file in glob.glob(cache+"/*")
        if not os.path.isdir(file)]
    dir.sort()
    dir.reverse()

    for mtime,file in dir:

        try:
            entry=minidom.parse(file)
            # determine source of entry
            source_id = _source_id_from_doc(entry)
            if not source_id:
                # no source determined, do not delete
                log.debug("No source found for %s", file)
                continue
            if source_id in entry_count:
                # subscribed to feed, update entry count
                entry_count[source_id] = entry_count[source_id] - 1
                if entry_count[source_id] >= 0:
                    # maximum not reached, do not delete
                    log.debug("Maximum not reached for %s from %s",
                        file, source_id)
                    continue
                else:
                    # maximum reached
                    log.debug("Removing %s, maximum reached for %s",
                        file, source_id)
            else:
                # not subscribed
                log.debug("Removing %s, not subscribed to %s",
                    file, source_id)
            # remove old entry
            os.unlink(file)

        except:
            log.error("Error parsing %s", file)

# end of expungeCache()
