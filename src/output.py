"""Built-in RSS and JSON output writers."""

import json
import os
import calendar
import hashlib
import urllib.parse
import urllib.request
from email.utils import formatdate
from xml.dom import minidom
from xml.sax.saxutils import escape

from . import config, media, net

RSS_OUTPUT_NAME = "news.xml"
NEWS_DIR_NAME = "news"
NEWS_INDEX_NAME = "news-index.json"
JSON_OUTPUT_NAME = NEWS_INDEX_NAME
OUTPUT_FILE_NAMES = (RSS_OUTPUT_NAME, JSON_OUTPUT_NAME)
LEGACY_OUTPUT_FILE_NAMES = ("rss.xml", "feed.json")
IMAGE_CACHE_DIR_NAME = "images"
MAX_IMAGE_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_EMBED_BYTES = 1 * 1024 * 1024


def image_cache_directory():
    """Return the cache directory used for downloaded entry images."""
    path = os.path.join(config.cache_directory(), IMAGE_CACHE_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def image_cache_key(url):
    """Return a deterministic cache key for one image URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _image_cache_paths(url):
    key = image_cache_key(url)
    directory = image_cache_directory()
    return (
        os.path.join(directory, key + ".img"),
        os.path.join(directory, key + ".json"),
    )


def validate_image_bytes(body):
    """Detect a supported image MIME type from raw bytes."""
    if not body:
        return None
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    if len(body) >= 16 and body[4:8] == b"ftyp" and b"avif" in body[8:16]:
        return "image/avif"
    return None


def _load_cached_image(url):
    image_path, meta_path = _image_cache_paths(url)
    if not (os.path.isfile(image_path) and os.path.isfile(meta_path)):
        return None
    try:
        with open(image_path, "rb") as handle:
            body = handle.read()
        with open(meta_path, "r", encoding="utf-8") as handle:
            metadata = json.load(handle)
    except (OSError, ValueError):
        return None
    mime_type = validate_image_bytes(body)
    if not mime_type:
        return None
    return {
        "url": url,
        "path": image_path,
        "mime_type": metadata.get("mime_type") or mime_type,
        "size": len(body),
    }


def fetch_cached_image(url, timeout=10):
    """Fetch one image URL to cache and return local metadata."""
    if not media.safe_public_http_url(url):
        raise ValueError("unsafe image url")
    cached = _load_cached_image(url)
    if cached:
        return cached

    request = urllib.request.Request(url, headers={"user-agent": "venus"})
    response = urllib.request.urlopen(request, timeout=timeout)
    body = net.read_limited_bytes(response, MAX_IMAGE_DOWNLOAD_BYTES, close=True)
    mime_type = validate_image_bytes(body)
    if not mime_type:
        raise ValueError("invalid image payload")

    image_path, meta_path = _image_cache_paths(url)
    with open(image_path, "wb") as handle:
        handle.write(body)
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "url": url,
                "mime_type": mime_type,
                "size": len(body),
            },
            handle,
            ensure_ascii=False,
        )
    return {
        "url": url,
        "path": image_path,
        "mime_type": mime_type,
        "size": len(body),
    }


def _direct_children(node, name):
    return [
        child for child in node.childNodes
        if child.nodeType == child.ELEMENT_NODE and child.localName == name
    ]


def _first_child(node, name):
    children = _direct_children(node, name)
    return children[0] if children else None


def _text(node):
    if node is None:
        return None
    return "".join(
        child.data for child in node.childNodes if child.nodeType == child.TEXT_NODE
    ) or None


def _element_text(node, name):
    return _text(_first_child(node, name))


def _child_xml(node):
    return "".join(child.toxml() for child in node.childNodes)


def _content_payload(node, name):
    element = _first_child(node, name)
    if element is None:
        return None, None
    payload = _child_xml(element)
    if not payload:
        payload = _text(element)
    return payload, element.getAttribute("type") or "text"


def _links(node):
    result = []
    for link in _direct_children(node, "link"):
        result.append({
            "rel": link.getAttribute("rel") or "alternate",
            "href": link.getAttribute("href"),
            "type": link.getAttribute("type") or None,
            "title": link.getAttribute("title") or None,
            "length": link.getAttribute("length") or None,
        })
    return result


def _categories(node):
    categories = []
    for category in _direct_children(node, "category"):
        term = category.getAttribute("term")
        if term:
            categories.append(term)
    return categories


def _planet_meta(node):
    meta = {}
    for child in node.childNodes:
        if child.nodeType != child.ELEMENT_NODE:
            continue
        if child.prefix == "planet":
            meta[child.localName] = _text(child)
    return meta


def _author(node):
    author = _first_child(node, "author")
    if author is None:
        return None
    return {
        "name": _element_text(author, "name"),
        "email": _element_text(author, "email"),
        "uri": _element_text(author, "uri"),
    }


def _source_dict(node):
    source = {
        "id": _element_text(node, "id"),
        "title": _element_text(node, "title"),
        "subtitle": _element_text(node, "subtitle"),
        "rights": _element_text(node, "rights"),
        "updated": _element_text(node, "updated"),
        "icon": _element_text(node, "icon"),
        "logo": _element_text(node, "logo"),
        "links": _links(node),
        "categories": _categories(node),
        "author": _author(node),
    }
    source.update(_planet_meta(node))
    source["screenshot"] = (
        source.get("screenshot")
        or source.get("logo")
        or source.get("icon")
    )
    return source


def _entry_dict(node):
    source_node = _first_child(node, "source")
    source = _source_dict(source_node) if source_node else {}
    title, title_type = _content_payload(node, "title")
    summary, summary_type = _content_payload(node, "summary")
    content, content_type = _content_payload(node, "content")
    entry = {
        "id": _element_text(node, "id"),
        "updated": _element_text(node, "updated"),
        "published": _element_text(node, "published"),
        "title": title,
        "title_type": title_type,
        "summary": summary,
        "summary_type": summary_type,
        "content": content,
        "content_type": content_type,
        "rights": _element_text(node, "rights"),
        "links": _links(node),
        "categories": _categories(node),
        "author": _author(node),
        "source": source,
    }
    entry["screenshot"] = media.entry_screenshot(entry, source)
    return entry


def _alternate_url(links):
    for link in links:
        if link.get("rel") == "alternate" and link.get("href"):
            return link.get("href")
    return links[0]["href"] if links else None


def _enclosures(entry):
    return [
        link for link in entry["links"]
        if link.get("rel") == "enclosure" and link.get("href")
    ]


def _format_rss_datetime(value):
    """Format an ISO-like feed timestamp for RSS when possible."""
    if not value:
        return None
    from src import feedparser
    parsed = feedparser._parse_date_w3dtf(value)
    if not parsed:
        parsed = feedparser._parse_date_iso8601(value)
    if not parsed:
        return None
    return formatdate(calendar.timegm(parsed), usegmt=True)


def _rss_author_text(author):
    """Render one RSS author string from normalized author metadata."""
    if not author:
        return None
    email = author.get("email")
    name = author.get("name")
    if email and name:
        return "%s (%s)" % (email, name)
    return email or name


def _channel_description(feed):
    """Return the best RSS channel description text."""
    return feed.get("subtitle") or feed["title"]


def _escape_cdata(value):
    """Escape CDATA terminators so attacker text cannot break RSS structure."""
    return value.replace("]]>", "]]]]><![CDATA[>")


def news_entry_name(position):
    """Return one numbered entry filename for `NEWS_DIR_NAME`."""
    return "%d.json" % position


def news_entry_relative_url(position):
    """Return one relative URL for one numbered news entry."""
    return "%s/%s" % (NEWS_DIR_NAME, news_entry_name(position))


def _json_item(entry):
    """Render one feed item as JSON Feed data."""
    source = entry["source"]
    attachments = []
    for enclosure in _enclosures(entry):
        attachments.append({
            "url": enclosure["href"],
            "mime_type": enclosure.get("type") or "application/octet-stream",
            "size_in_bytes": int(enclosure["length"]) if enclosure.get("length") and enclosure["length"].isdigit() else None,
        })

    item = {
        "id": entry["id"],
        "url": _alternate_url(entry["links"]),
        "title": entry["title"],
        "content_html": entry["content"] or entry["summary"],
        "summary": entry["summary"],
        "date_published": entry["published"],
        "date_modified": entry["updated"],
        "tags": entry["categories"],
        "attachments": [attachment for attachment in attachments if attachment["url"]],
        "image": entry["screenshot"],
        "_source": {
            "id": source.get("id"),
            "title": source.get("title"),
            "url": _alternate_url(source.get("links", [])),
            "subtitle": source.get("subtitle"),
            "icon": source.get("icon"),
            "logo": source.get("logo"),
            "screenshot": source.get("screenshot"),
            "author": source.get("author"),
            "categories": source.get("categories", []),
            "planet": {key: value for key, value in source.items() if key.startswith("planet_")},
        },
    }
    author = entry.get("author") or {}
    if author.get("name") or author.get("uri"):
        item["authors"] = [{
            "name": author.get("name"),
            "url": author.get("uri"),
        }]
    return item


def _news_source(source):
    """Build the compact source object for one numbered news entry."""
    payload = {
        "id": source.get("id"),
        "title": source.get("title"),
        "url": _alternate_url(source.get("links", [])),
    }
    return {key: value for key, value in payload.items() if value}


def _news_author(author):
    """Build the compact author object for one numbered news entry."""
    payload = {
        "name": author.get("name"),
        "url": author.get("uri"),
    }
    return {key: value for key, value in payload.items() if value}


def _news_image(entry, image_loader=None):
    """Build one compact image object for one numbered news entry."""
    image_url = entry.get("screenshot")
    if not image_url:
        return None
    if image_loader:
        image = image_loader(image_url)
        if image:
            return image
    return {"url": image_url}


def _news_entry_dict(entry, image_loader=None):
    """Build the compact entry payload for one numbered news JSON file."""
    payload = {
        "id": entry["id"],
        "url": _alternate_url(entry["links"]),
        "title": entry["title"],
        "summary": entry["summary"],
        "date": entry["published"] or entry["updated"],
        "tags": entry["categories"],
    }
    if entry.get("content"):
        payload["content"] = entry["content"]
    source = _news_source(entry.get("source") or {})
    if source:
        payload["source"] = source
    author = _news_author(entry.get("author") or {})
    if author:
        payload["author"] = author
    image = _news_image(entry, image_loader=image_loader)
    if image:
        payload["image"] = image
    return payload


def render_news_entry(entry, image_loader=None):
    """Render one compact numbered-news entry as JSON text."""
    return json.dumps(
        _news_entry_dict(entry, image_loader=image_loader),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def render_news_index(entries):
    """Render the compact news index manifest as JSON text."""
    urls = [
        news_entry_relative_url(position)
        for position in range(1, len(entries) + 1)
    ]
    return json.dumps(
        {
            "total": len(entries),
            "urls": urls,
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _build_feed_dict(doc):
    """Build the intermediate feed model shared by RSS and JSON serializers."""
    feed = doc.documentElement
    title, _ = _content_payload(feed, "title")
    subtitle, _ = _content_payload(feed, "subtitle")
    links = _links(feed)
    home = _alternate_url(links) or config.link()
    author = _author(feed)
    entries = [_entry_dict(node) for node in _direct_children(feed, "entry")]
    return {
        "title": title or config.name(),
        "subtitle": subtitle,
        "description": subtitle or title or config.name(),
        "updated": _element_text(feed, "updated"),
        "rights": _element_text(feed, "rights"),
        "links": links,
        "home_page_url": home,
        "feed_url": home and urllib.parse.urljoin(home.rstrip("/") + "/", JSON_OUTPUT_NAME) or None,
        "author": author,
        "entries": entries,
        "items": [_json_item(entry) for entry in entries],
    }


def build_feed_model(doc):
    """Return the normalized aggregate feed model used by built-in outputs."""
    if isinstance(doc, bytes):
        doc = doc.decode("utf-8")
    return _build_feed_dict(minidom.parseString(doc))


def _rss_item_xml(entry):
    """Render one feed item as RSS item XML."""
    parts = ["<item>"]
    if entry["title"]:
        parts.append(f"<title>{escape(entry['title'])}</title>")
    link = _alternate_url(entry["links"])
    if link:
        parts.append(f"<link>{escape(link)}</link>")
    if entry["id"]:
        is_permalink = "true" if link and entry["id"] == link else "false"
        parts.append(f'<guid isPermaLink="{is_permalink}">{escape(entry["id"])}</guid>')
    pub_date = _format_rss_datetime(entry["published"] or entry["updated"])
    if pub_date:
        parts.append(f"<pubDate>{pub_date}</pubDate>")
    if entry["summary"]:
        parts.append(f"<description><![CDATA[{_escape_cdata(entry['summary'])}]]></description>")
    elif entry["content"]:
        parts.append(f"<description><![CDATA[{_escape_cdata(entry['content'])}]]></description>")
    if entry["content"]:
        parts.append(f"<content:encoded><![CDATA[{_escape_cdata(entry['content'])}]]></content:encoded>")
    author = _rss_author_text(entry.get("author") or {})
    if author:
        parts.append(f"<author>{escape(author)}</author>")
    for category in entry["categories"]:
        parts.append(f"<category>{escape(category)}</category>")
    for enclosure in _enclosures(entry):
        parts.append(
            '<enclosure url="{url}" type="{type}" length="{length}" />'.format(
                url=escape(enclosure["href"]),
                type=escape(enclosure.get("type") or "application/octet-stream"),
                length=escape(enclosure.get("length") or "0"),
            )
        )
    if entry["screenshot"]:
        parts.append(
            f'<media:thumbnail url="{escape(entry["screenshot"])}" />'
        )
    source = entry["source"]
    source_url = _alternate_url(source.get("links", []))
    if source.get("title") and source_url:
        parts.append(
            f'<source url="{escape(source_url)}">{escape(source["title"])}</source>'
        )
    if source.get("title"):
        parts.append(f"<planet:source_title>{escape(source['title'])}</planet:source_title>")
    if source.get("id"):
        parts.append(f"<planet:source_id>{escape(source['id'])}</planet:source_id>")
    if source.get("screenshot"):
        parts.append(
            f"<planet:source_screenshot>{escape(source['screenshot'])}</planet:source_screenshot>"
        )
    parts.append("</item>")
    return "".join(parts)


def render_rss(feed):
    """Render the intermediate feed model as RSS XML."""
    rss_parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
        'xmlns:media="http://search.yahoo.com/mrss/" '
        'xmlns:planet="http://planet.intertwingly.net/">',
        "<channel>",
        f"<title>{escape(feed['title'])}</title>",
    ]
    if feed["home_page_url"]:
        rss_parts.append(f"<link>{escape(feed['home_page_url'])}</link>")
    rss_parts.append(f"<description>{escape(_channel_description(feed))}</description>")
    last_build = _format_rss_datetime(feed.get("updated"))
    if last_build:
        rss_parts.append(f"<lastBuildDate>{last_build}</lastBuildDate>")
    if feed.get("rights"):
        rss_parts.append(f"<copyright>{escape(feed['rights'])}</copyright>")
    author = _rss_author_text(feed.get("author") or {})
    if author:
        rss_parts.append(f"<managingEditor>{escape(author)}</managingEditor>")
    for entry in feed["entries"]:
        rss_parts.append(_rss_item_xml(entry))
    rss_parts.extend(["</channel>", "</rss>"])
    return "".join(rss_parts)


def render_json(feed):
    """Render the intermediate feed model as JSON Feed text."""
    json_feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": feed["title"],
        "home_page_url": feed["home_page_url"],
        "feed_url": feed["feed_url"],
        "description": feed["subtitle"],
        "items": feed["items"],
    }
    if feed["author"] and (feed["author"].get("name") or feed["author"].get("uri")):
        json_feed["authors"] = [{
            "name": feed["author"].get("name"),
            "url": feed["author"].get("uri"),
        }]
    return json.dumps(json_feed, indent=2, ensure_ascii=False) + "\n"


def write_outputs(doc):
    """Write the built-in output files to the configured output directory."""
    feed = build_feed_model(doc)
    output_dir = config.output_dir()
    os.makedirs(output_dir, exist_ok=True)

    # Remove legacy maintained files that are no longer current outputs.
    for legacy_name in LEGACY_OUTPUT_FILE_NAMES:
        if legacy_name in OUTPUT_FILE_NAMES:
            continue
        legacy_path = os.path.join(output_dir, legacy_name)
        if os.path.isfile(legacy_path):
            os.remove(legacy_path)

    rss_path = os.path.join(output_dir, RSS_OUTPUT_NAME)
    with open(rss_path, "w", encoding="utf-8") as handle:
        handle.write(render_rss(feed))

    news_dir = os.path.join(output_dir, NEWS_DIR_NAME)
    os.makedirs(news_dir, exist_ok=True)
    expected_entry_names = set()
    for position, entry in enumerate(feed["entries"], start=1):
        entry_name = news_entry_name(position)
        expected_entry_names.add(entry_name)
        news_entry_path = os.path.join(news_dir, entry_name)
        tmp_path = os.path.join(news_dir, ".%s.tmp" % entry_name)
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(render_news_entry(entry))
        os.replace(tmp_path, news_entry_path)

    # Remove stale numbered entries while preserving unrelated files.
    for entry_name in os.listdir(news_dir):
        if not entry_name.endswith(".json"):
            continue
        stem = entry_name[:-5]
        if not stem.isdigit():
            continue
        if entry_name in expected_entry_names:
            continue
        os.remove(os.path.join(news_dir, entry_name))

    news_index_path = os.path.join(output_dir, JSON_OUTPUT_NAME)
    tmp_index_path = os.path.join(output_dir, ".%s.tmp" % JSON_OUTPUT_NAME)
    with open(tmp_index_path, "w", encoding="utf-8") as handle:
        handle.write(render_news_index(feed["entries"]))
    os.replace(tmp_index_path, news_index_path)
