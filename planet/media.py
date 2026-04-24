"""Helpers for extracting feed and page media metadata."""

from html.parser import HTMLParser
import os
import re
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


def feed_screenshot(feed, cached=None):
    """Choose the best available source screenshot URL."""
    if feed.get("planet_screenshot"):
        return feed.get("planet_screenshot")
    if cached:
        return cached
    if feed.get("logo"):
        return feed.get("logo")
    if feed.get("icon"):
        return feed.get("icon")
    if "image" in feed and feed.image.get("href"):
        return feed.image.get("href")

    homepage = feed_homepage(feed)
    if not homepage:
        return None
    if urllib.parse.urlparse(homepage).scheme not in ("http", "https", "file"):
        return None

    try:
        return fetch_open_graph_image(homepage)
    except OSError:
        return None
    except ValueError:
        return None


def entry_screenshot(entry, source=None):
    """Choose the best image for one entry, falling back to its source."""
    for link in entry.get("links", []):
        href = link.get("href")
        if not href:
            continue
        if link.get("rel") == "enclosure" and looks_like_image(href, link.get("type")):
            return href

    for detail_name in ("content_detail", "summary_detail", "title_detail"):
        detail = entry.get(detail_name)
        if detail and detail.get("value"):
            image = first_image_from_html(detail.get("value"), detail.get("base"))
            if image:
                return image

    if source:
        return (
            source.get("planet_screenshot")
            or source.get("logo")
            or source.get("icon")
            or None
        )
    return None
