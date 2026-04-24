"""Built-in RSS and JSON output writers."""

import json
import os
import time
import urllib.parse
from email.utils import formatdate
from xml.dom import minidom
from xml.sax.saxutils import escape

from . import config, media


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


def _rss_item_xml(entry):
    parts = ["<item>"]
    if entry["title"]:
        parts.append(f"<title>{escape(entry['title'])}</title>")
    link = _alternate_url(entry["links"])
    if link:
        parts.append(f"<link>{escape(link)}</link>")
    if entry["id"]:
        parts.append(f"<guid>{escape(entry['id'])}</guid>")
    when = entry["published"] or entry["updated"]
    if when:
        try:
            pub_ts = time.mktime(time.strptime(when, "%Y-%m-%dT%H:%M:%SZ"))
            parts.append(f"<pubDate>{formatdate(pub_ts, usegmt=True)}</pubDate>")
        except ValueError:
            pass
    if entry["summary"]:
        parts.append(f"<description><![CDATA[{entry['summary']}]]></description>")
    elif entry["content"]:
        parts.append(f"<description><![CDATA[{entry['content']}]]></description>")
    if entry["content"]:
        parts.append(f"<content:encoded><![CDATA[{entry['content']}]]></content:encoded>")
    author = entry.get("author") or {}
    if author.get("email"):
        parts.append(f"<author>{escape(author['email'])}</author>")
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


def _json_item(entry):
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


def _feed_dict(doc):
    feed = doc.documentElement
    entries = [_entry_dict(node) for node in _direct_children(feed, "entry")]
    title, _ = _content_payload(feed, "title")
    subtitle, _ = _content_payload(feed, "subtitle")
    links = _links(feed)
    author = _author(feed)
    return {
        "title": title or config.name(),
        "subtitle": subtitle,
        "updated": _element_text(feed, "updated"),
        "links": links,
        "author": author,
        "entries": entries,
    }


def write_outputs(doc):
    """Write `rss.xml` and `feed.json` to the configured output directory."""
    if isinstance(doc, bytes):
        doc = doc.decode("utf-8")
    xdoc = minidom.parseString(doc)
    feed = _feed_dict(xdoc)
    output_dir = config.output_dir()
    os.makedirs(output_dir, exist_ok=True)

    rss_parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
        'xmlns:media="http://search.yahoo.com/mrss/" '
        'xmlns:planet="http://planet.intertwingly.net/">',
        "<channel>",
        f"<title>{escape(feed['title'])}</title>",
    ]
    home = _alternate_url(feed["links"]) or config.link()
    if home:
        rss_parts.append(f"<link>{escape(home)}</link>")
    if feed["subtitle"]:
        rss_parts.append(f"<description>{escape(feed['subtitle'])}</description>")
    else:
        rss_parts.append(f"<description>{escape(feed['title'])}</description>")
    for entry in feed["entries"]:
        rss_parts.append(_rss_item_xml(entry))
    rss_parts.extend(["</channel>", "</rss>"])

    rss_path = os.path.join(output_dir, "rss.xml")
    with open(rss_path, "w", encoding="utf-8") as handle:
        handle.write("".join(rss_parts))

    json_feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": feed["title"],
        "home_page_url": home,
        "feed_url": home and urllib.parse.urljoin(home.rstrip("/") + "/", "feed.json") or None,
        "description": feed["subtitle"],
        "items": [_json_item(entry) for entry in feed["entries"]],
    }
    if feed["author"] and (feed["author"].get("name") or feed["author"].get("uri")):
        json_feed["authors"] = [{
            "name": feed["author"].get("name"),
            "url": feed["author"].get("uri"),
        }]

    json_path = os.path.join(output_dir, "feed.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(json_feed, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
