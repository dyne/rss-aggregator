"""Helpers for extracting feed and page media metadata."""

from html.parser import HTMLParser
import ipaddress
import os
import re
import socket
import urllib.parse
import urllib.request


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif")
IMG_RE = re.compile(r"""<img[^>]+src=['"]([^'"]+)['"]""", re.IGNORECASE)


def looks_like_image(url, mime_type=None):
    """Return True when a URL or MIME type looks image-like."""
    if mime_type and mime_type.startswith("image/"):
        return True
    lower = url.lower()
    return any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS)


def _is_public_ip(value):
    """Return True when an IP address is globally routable."""
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def safe_public_http_url(url, resolver=None):
    """Return True when a URL is HTTP(S) and resolves to public IPs only."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc or parsed.username or parsed.password:
        return False
    host = parsed.hostname
    if not host:
        return False

    try:
        ipaddress.ip_address(host)
        return _is_public_ip(host)
    except ValueError:
        pass

    resolver = resolver or socket.getaddrinfo
    try:
        resolved = resolver(host, None)
    except OSError:
        return False
    if not resolved:
        return False

    for row in resolved:
        ip = row[4][0]
        try:
            if not _is_public_ip(ip):
                return False
        except ValueError:
            return False
    return True


def first_image_from_html(value, base_url=None):
    """Extract the first image URL from HTML content."""
    if not value:
        return None
    match = IMG_RE.search(value)
    if not match:
        return None
    url = match.group(1)
    if base_url:
        url = urllib.parse.urljoin(base_url, url)
    return url


class OpenGraphParser(HTMLParser):
    """Collect the first useful image candidate from HTML metadata."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.image = None

    def handle_starttag(self, tag, attrs):
        if self.image:
            return
        attrs = dict(attrs)
        if tag == "meta":
            prop = attrs.get("property") or attrs.get("name")
            if prop in ("og:image", "twitter:image", "twitter:image:src"):
                content = attrs.get("content")
                if content:
                    self.image = urllib.parse.urljoin(self.base_url, content)
        elif tag == "link":
            rel = attrs.get("rel", "").lower()
            href = attrs.get("href")
            if href and rel in ("icon", "shortcut icon", "apple-touch-icon"):
                self.image = urllib.parse.urljoin(self.base_url, href)


def fetch_open_graph_image(url, timeout=10):
    """Fetch one source page and return its first useful image metadata URL."""
    if not safe_public_http_url(url):
        raise ValueError("unsafe url")
    request = urllib.request.Request(url, headers={"user-agent": "venus"})
    response = urllib.request.urlopen(request, timeout=timeout)
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type:
        return None
    body = response.read(262144).decode("utf-8", "replace")
    parser = OpenGraphParser(url)
    parser.feed(body)
    return parser.image


def feed_homepage(feed):
    """Return the best homepage URL for a parsed feed."""
    for link in feed.get("links", []):
        if link.get("rel") == "alternate" and link.get("href"):
            return link.get("href")
    return feed.get("link")


def source_screenshot(source):
    """Return the best source-level screenshot candidate already in hand."""
    if not source:
        return None
    if source.get("screenshot"):
        return source.get("screenshot")
    if source.get("planet_screenshot"):
        return source.get("planet_screenshot")
    if source.get("logo"):
        return source.get("logo")
    if source.get("icon"):
        return source.get("icon")
    if "image" in source and source.image.get("href"):
        return source.image.get("href")
    return None


def should_refresh_screenshot(homepage, cached_homepage):
    """Return True when homepage-derived screenshot metadata should refresh."""
    if not homepage or not cached_homepage:
        return False
    return homepage != cached_homepage


def feed_screenshot(feed, cached=None, cached_homepage=None):
    """Choose the best available source screenshot URL.

    Feed-declared image metadata wins over cache. Homepage-derived cached
    screenshots are reused until the feed homepage changes.
    """
    declared = source_screenshot(feed)
    if declared:
        return declared

    homepage = feed_homepage(feed)
    if cached and not should_refresh_screenshot(homepage, cached_homepage):
        return cached

    if not homepage:
        return cached
    if not safe_public_http_url(homepage):
        return cached

    try:
        screenshot = fetch_open_graph_image(homepage)
        return screenshot or cached
    except OSError:
        return cached
    except ValueError:
        return cached


def entry_image_from_enclosures(entry):
    """Return the first image enclosure URL for one entry."""
    for link in entry.get("links", []):
        href = link.get("href")
        if not href:
            continue
        if link.get("rel") == "enclosure" and looks_like_image(href, link.get("type")):
            return href
    return None


def entry_image_from_html(entry):
    """Return the first inline HTML image URL for one entry."""
    for detail_name in ("content_detail", "summary_detail", "title_detail"):
        detail = entry.get(detail_name)
        if detail and detail.get("value"):
            image = first_image_from_html(detail.get("value"), detail.get("base"))
            if image:
                return image
    return None


def source_fallback_screenshot(source):
    """Return the source screenshot used when an entry has no item image."""
    if not source:
        return None
    return (
        source.get("screenshot")
        or source.get("planet_screenshot")
        or source.get("logo")
        or source.get("icon")
        or None
    )


def entry_screenshot(entry, source=None):
    """Choose the best image for one entry.

    The precedence is fixed and tested: image enclosure, first inline HTML
    image from content/summary/title, then the source-level screenshot.
    """
    return (
        entry_image_from_enclosures(entry)
        or entry_image_from_html(entry)
        or source_fallback_screenshot(source)
    )
