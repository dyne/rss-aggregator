"""Rewrite Lemmy wrapper posts to their upstream target page."""

from html.parser import HTMLParser
import urllib.parse

from src import feedparser

from . import media


LEMMY_INTERNAL_PREFIXES = ("/u/", "/c/", "/post/", "/comment/")


class _LinkCollector(HTMLParser):
    """Collect anchor URLs from one HTML fragment in document order."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def _detail_nodes(entry):
    """Yield summary/content detail dictionaries that may hold Lemmy HTML."""
    for name in ("summary_detail", "content_detail"):
        detail = entry.get(name)
        if detail and detail.get("value"):
            yield detail
    for detail in entry.get("content", []):
        if detail and detail.get("value"):
            yield detail


def _normalize_url(url, base_url=None):
    """Resolve one candidate URL against an optional base URL."""
    if not url:
        return None
    resolved = urllib.parse.urljoin(base_url or "", url)
    parsed = urllib.parse.urlparse(resolved)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return resolved


def _is_lemmy_internal(url, entry_host):
    """Return True when a URL points back into the Lemmy wrapper itself."""
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname != entry_host:
        return False
    return parsed.path.startswith(LEMMY_INTERNAL_PREFIXES)


def _entry_host(entry):
    """Return the hostname of the original Lemmy post URL when present."""
    return urllib.parse.urlparse(entry.get("link", "")).hostname


def _text_detail(value, base_url):
    """Create one text/plain detail node for reconstitution."""
    return feedparser.FeedParserDict({
        "type": "text/plain",
        "value": value,
        "base": base_url,
    })


def _set_text_field(entry, name, value, base_url):
    """Replace a content-like entry field with plain rendered text."""
    entry[name] = value
    entry[name + "_detail"] = _text_detail(value, base_url)


def first_upstream_link(entry, safe_url=media.safe_public_http_url):
    """Return the first public non-Lemmy target URL for one Lemmy entry."""
    entry_host = _entry_host(entry)

    for link in entry.get("links", []):
        href = _normalize_url(link.get("href"))
        if not href:
            continue
        if _is_lemmy_internal(href, entry_host):
            continue
        if safe_url(href):
            return href

    for detail in _detail_nodes(entry):
        parser = _LinkCollector()
        parser.feed(detail.get("value", ""))
        for href in parser.links:
            candidate = _normalize_url(href, detail.get("base"))
            if not candidate:
                continue
            if _is_lemmy_internal(candidate, entry_host):
                continue
            if safe_url(candidate):
                return candidate

    return None


def _rewrite_links(entry, upstream_url, image_url):
    """Build the entry links exposed after Lemmy rewriting."""
    links = [feedparser.FeedParserDict({
        "rel": "alternate",
        "href": upstream_url,
        "type": "text/html",
    })]

    seen = {upstream_url}
    for link in entry.get("links", []):
        href = _normalize_url(link.get("href"))
        if not href or href in seen:
            continue
        if link.get("rel") != "enclosure":
            continue
        if not media.looks_like_image(href, link.get("type")):
            continue
        kept = feedparser.FeedParserDict(link.copy())
        kept["href"] = href
        links.append(kept)
        seen.add(href)

    if image_url and image_url not in seen:
        links.append(feedparser.FeedParserDict({
            "rel": "enclosure",
            "href": image_url,
            "type": "image/*",
            "length": "0",
        }))

    return links


def rewrite_entry(entry, metadata_fetcher=None):
    """Rewrite one Lemmy wrapper entry to point at its upstream page."""
    metadata_fetcher = metadata_fetcher or media.fetch_page_metadata
    upstream_url = first_upstream_link(entry)
    if not upstream_url:
        return False

    try:
        metadata = metadata_fetcher(upstream_url) or {}
    except (OSError, ValueError):
        metadata = {}

    image_url = metadata.get("image")
    if image_url and not media.safe_public_http_url(image_url):
        image_url = None

    entry["id"] = upstream_url
    entry["link"] = upstream_url
    entry["links"] = _rewrite_links(entry, upstream_url, image_url)

    title = metadata.get("title") or entry.get("title") or upstream_url
    _set_text_field(entry, "title", title, upstream_url)

    summary = metadata.get("summary")
    if summary:
        _set_text_field(entry, "summary", summary, upstream_url)
    else:
        entry.pop("summary", None)
        entry.pop("summary_detail", None)

    entry.pop("content", None)
    entry.pop("content_detail", None)
    entry.pop("author", None)
    entry.pop("author_detail", None)
    return True


def rewrite_entries(entries):
    """Rewrite each Lemmy entry in-place, skipping entries without targets."""
    for entry in entries:
        rewrite_entry(entry)
