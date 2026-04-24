import os, sys
import urllib.parse
import urllib.request
import urllib.error
import planet

class PublishError(Exception):
    """Raised when a hub publish request fails."""

def publish_urls(hub, urls):
    """Publish updated feed URLs to a PubSubHubbub/WebSub hub."""
    data = urllib.parse.urlencode(
        {'hub.url': urls, 'hub.mode': 'publish'}, doseq=True)
    request = urllib.request.Request(hub, data=data.encode('utf-8'))
    try:
        urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return
        error = e.read().decode('utf-8', 'replace') if hasattr(e, 'read') else ''
        raise PublishError('%s, Response: "%s"' % (e, error))
    except OSError as e:
        raise PublishError(str(e))

def publish(config):
    log = planet.logger
    hub = config.pubsubhubbub_hub()
    link = config.link()

    # identify feeds
    feeds = []
    if hub and link:
        for root, dirs, files in os.walk(config.output_dir()):
            for file in files:
                 if file in config.pubsubhubbub_feeds():
                     feeds.append(urllib.parse.urljoin(link, file))

    # publish feeds
    if feeds:
        try:
            publish_urls(hub, feeds)
            for feed in feeds:
                log.info("Published %s to %s\n" % (feed, hub))
        except PublishError as e:
            log.error("PubSubHubbub publishing error: %s\n" % e)
