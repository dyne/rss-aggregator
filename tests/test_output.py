#!/usr/bin/env python

import json
import os
import shutil
import unittest
from xml.dom import minidom

from src import config, output, splice

workdir = 'tests/work/apply'
configfile = 'tests/data/apply/config-asf.ini'
testfeed = 'tests/data/apply/feed.xml'


class OutputTest(unittest.TestCase):
    def setUp(self):
        with open(testfeed, encoding='utf-8') as testfile:
            self.feeddata = testfile.read()

        try:
            os.makedirs(workdir)
        except OSError:
            self.tearDown()
            os.makedirs(workdir)

    def tearDown(self):
        if os.path.exists(os.path.split(workdir)[0]):
            shutil.rmtree(os.path.split(workdir)[0])

    def test_apply_writes_rss_and_json(self):
        config.load(configfile)
        splice.apply(self.feeddata)

        rss_path = os.path.join(workdir, output.RSS_OUTPUT_NAME)
        json_path = os.path.join(workdir, output.JSON_OUTPUT_NAME)

        self.assertTrue(os.path.exists(rss_path))
        self.assertTrue(os.path.exists(json_path))

        rss = minidom.parse(rss_path)
        self.assertEqual('rss', rss.documentElement.tagName)
        self.assertEqual(12, len(rss.getElementsByTagName('item')))
        self.assertEqual('test planet',
            rss.getElementsByTagName('title')[0].firstChild.nodeValue)

        with open(json_path, encoding='utf-8') as handle:
            feed = json.load(handle)
        self.assertEqual('https://jsonfeed.org/version/1.1', feed['version'])
        self.assertEqual('test planet', feed['title'])
        self.assertEqual(12, len(feed['items']))
        self.assertEqual('tag:planet.intertwingly.net,2006:testfeed3/2',
            feed['items'][0]['id'])
        self.assertEqual('Sam Ruby',
            feed['items'][0]['_source']['title'])

    def test_output_names_are_fixed_constants(self):
        self.assertEqual('rss.xml', output.RSS_OUTPUT_NAME)
        self.assertEqual('feed.json', output.JSON_OUTPUT_NAME)
        self.assertEqual(
            ('rss.xml', 'feed.json'),
            output.OUTPUT_FILE_NAMES)

    def test_build_feed_model_centralizes_output_fields(self):
        config.load(configfile)
        feed = output.build_feed_model(self.feeddata)
        self.assertEqual('test planet', feed['title'])
        self.assertEqual('', feed['home_page_url'])
        self.assertEqual(None, feed['feed_url'])
        self.assertEqual(12, len(feed['items']))
        self.assertEqual(
            'tag:planet.intertwingly.net,2006:testfeed3/2',
            feed['items'][0]['id'])

    def test_apply_serializes_entry_and_source_images(self):
        config.load(configfile)
        doc = (
            '<feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:planet="http://planet.intertwingly.net/">'
            '<title>Media Planet</title>'
            '<rights>Copyright Example</rights>'
            '<link rel="alternate" href="http://planet.example/" />'
            '<entry>'
            '<id>tag:example.com,2026:1</id>'
            '<title>With enclosure</title>'
            '<updated>2026-04-24T12:00:00Z</updated>'
            '<link rel="alternate" href="http://example.com/post-1" />'
            '<link rel="enclosure" href="http://example.com/post-1.jpg" type="image/jpeg" length="12" />'
            '<source>'
            '<title>Feed One</title>'
            '<link rel="alternate" href="http://example.com/" />'
            '<planet:screenshot>http://example.com/source.png</planet:screenshot>'
            '</source>'
            '</entry>'
            '<entry>'
            '<id>tag:example.com,2026:2</id>'
            '<title>Source fallback</title>'
            '<updated>2026-04-24T11:00:00Z</updated>'
            '<link rel="alternate" href="http://example.com/post-2" />'
            '<source>'
            '<title>Feed Two</title>'
            '<link rel="alternate" href="http://example.org/" />'
            '<planet:screenshot>http://example.org/source.png</planet:screenshot>'
            '</source>'
            '</entry>'
            '</feed>'
        )

        splice.apply(doc)

        rss = minidom.parse(os.path.join(workdir, output.RSS_OUTPUT_NAME))
        thumbnails = rss.getElementsByTagName('media:thumbnail')
        self.assertEqual(
            ['http://example.com/post-1.jpg', 'http://example.org/source.png'],
            [node.getAttribute('url') for node in thumbnails])
        self.assertEqual(
            'Copyright Example',
            rss.getElementsByTagName('copyright')[0].firstChild.nodeValue)
        sources = rss.getElementsByTagName('source')
        self.assertEqual(
            ['http://example.com/', 'http://example.org/'],
            [node.getAttribute('url') for node in sources])

        with open(os.path.join(workdir, output.JSON_OUTPUT_NAME), encoding='utf-8') as handle:
            feed = json.load(handle)

        self.assertEqual('http://example.com/post-1.jpg', feed['items'][0]['image'])
        self.assertEqual('http://example.org/source.png', feed['items'][1]['image'])
        self.assertEqual('http://example.org/source.png', feed['items'][1]['_source']['screenshot'])

    def test_apply_writes_rss_metadata_with_dates_and_author(self):
        config.load(configfile)
        splice.apply(self.feeddata)

        rss = minidom.parse(os.path.join(workdir, output.RSS_OUTPUT_NAME))
        channel = rss.getElementsByTagName('channel')[0]
        self.assertEqual(
            'Sat, 14 Oct 2006 13:02:18 GMT',
            channel.getElementsByTagName('lastBuildDate')[0].firstChild.nodeValue)
        self.assertEqual(
            'Anonymous Coward',
            channel.getElementsByTagName('managingEditor')[0].firstChild.nodeValue)

        first_item = rss.getElementsByTagName('item')[0]
        self.assertEqual(
            'Sat, 14 Oct 2006 13:02:18 GMT',
            first_item.getElementsByTagName('pubDate')[0].firstChild.nodeValue)
        guid = first_item.getElementsByTagName('guid')[0]
        self.assertEqual('false', guid.getAttribute('isPermaLink'))

    def test_rss_helper_fallbacks(self):
        self.assertEqual(None, output._format_rss_datetime(None))
        self.assertEqual(None, output._format_rss_datetime("not-a-date"))
        self.assertEqual("person@example.com (Example Person)",
            output._rss_author_text({"email": "person@example.com", "name": "Example Person"}))
        self.assertEqual("person@example.com",
            output._rss_author_text({"email": "person@example.com"}))
        self.assertEqual("Example Person",
            output._rss_author_text({"name": "Example Person"}))
        self.assertEqual(None, output._rss_author_text({}))
        self.assertEqual("Subtitle wins",
            output._channel_description({"title": "Feed Title", "subtitle": "Subtitle wins"}))
        self.assertEqual("Feed Title",
            output._channel_description({"title": "Feed Title", "subtitle": None}))

    def test_render_rss_handles_permalink_and_fallback_fields(self):
        rss = output.render_rss({
            "title": "Fallback Feed",
            "subtitle": None,
            "updated": "not-a-date",
            "rights": None,
            "home_page_url": "http://planet.example/",
            "author": {"name": "Maintainer"},
            "entries": [
                {
                    "title": "Summary Entry",
                    "id": "http://example.com/permalink",
                    "published": None,
                    "updated": "2026-04-24T12:00:00Z",
                    "summary": "<p>Summary only</p>",
                    "content": None,
                    "links": [{"rel": "alternate", "href": "http://example.com/permalink"}],
                    "categories": ["alpha"],
                    "author": {"name": "Author One"},
                    "screenshot": None,
                    "source": {"title": None, "id": None, "links": [], "screenshot": None},
                },
                {
                    "title": "Content Entry",
                    "id": "tag:example.com,2026:2",
                    "published": "not-a-date",
                    "updated": None,
                    "summary": None,
                    "content": "<p>Content only</p>",
                    "links": [
                        {"rel": "alternate", "href": "http://example.com/content"},
                        {"rel": "enclosure", "href": "http://example.com/file.bin", "type": None, "length": None},
                    ],
                    "categories": [],
                    "author": {"email": "author@example.com"},
                    "screenshot": "http://example.com/thumb.png",
                    "source": {
                        "title": "Source Feed",
                        "id": "source:1",
                        "links": [{"rel": "alternate", "href": "http://example.com/source"}],
                        "screenshot": "http://example.com/source.png",
                    },
                },
            ],
        })

        document = minidom.parseString(rss)
        channel = document.getElementsByTagName("channel")[0]
        self.assertEqual(
            "Fallback Feed",
            channel.getElementsByTagName("description")[0].firstChild.nodeValue)
        self.assertEqual(0, len(channel.getElementsByTagName("lastBuildDate")))
        self.assertEqual(
            "Maintainer",
            channel.getElementsByTagName("managingEditor")[0].firstChild.nodeValue)

        items = document.getElementsByTagName("item")
        first_guid = items[0].getElementsByTagName("guid")[0]
        self.assertEqual("true", first_guid.getAttribute("isPermaLink"))
        self.assertEqual(
            "<p>Summary only</p>",
            items[0].getElementsByTagName("description")[0].firstChild.nodeValue)
        self.assertEqual(0, len(items[0].getElementsByTagName("content:encoded")))

        second_item = items[1]
        self.assertEqual(0, len(second_item.getElementsByTagName("pubDate")))
        self.assertEqual(
            "<p>Content only</p>",
            second_item.getElementsByTagName("description")[0].firstChild.nodeValue)
        self.assertEqual(
            "<p>Content only</p>",
            second_item.getElementsByTagName("content:encoded")[0].firstChild.nodeValue)
        enclosure = second_item.getElementsByTagName("enclosure")[0]
        self.assertEqual("application/octet-stream", enclosure.getAttribute("type"))
        self.assertEqual("0", enclosure.getAttribute("length"))
        source = second_item.getElementsByTagName("source")[0]
        self.assertEqual("http://example.com/source", source.getAttribute("url"))

    def test_json_item_and_feed_fallbacks(self):
        item = output._json_item({
            "id": "tag:example.com,2026:json",
            "updated": "2026-04-24T12:00:00Z",
            "published": None,
            "title": "JSON Entry",
            "summary": "<p>Summary</p>",
            "content": None,
            "categories": ["alpha"],
            "links": [
                {"rel": "enclosure", "href": "", "type": "image/png", "length": "12"},
                {"rel": "enclosure", "href": "http://example.com/a.bin", "type": None, "length": "bad"},
                {"rel": "alternate", "href": "http://example.com/post"},
            ],
            "author": {"name": "Entry Author", "uri": "http://example.com/authors/entry"},
            "screenshot": "http://example.com/item.png",
            "source": {
                "id": "source:json",
                "title": "JSON Source",
                "subtitle": None,
                "icon": None,
                "logo": None,
                "screenshot": "http://example.com/source.png",
                "author": None,
                "categories": [],
                "links": [{"rel": "related", "href": "http://example.com/source"}],
                "planet_name": "Venus",
            },
        })

        self.assertEqual("http://example.com/post", item["url"])
        self.assertEqual(
            [{"url": "http://example.com/a.bin", "mime_type": "application/octet-stream", "size_in_bytes": None}],
            item["attachments"])
        self.assertEqual(
            [{"name": "Entry Author", "url": "http://example.com/authors/entry"}],
            item["authors"])
        self.assertEqual("http://example.com/source", item["_source"]["url"])
        self.assertEqual({"planet_name": "Venus"}, item["_source"]["planet"])

        json_feed = json.loads(output.render_json({
            "title": "JSON Feed",
            "home_page_url": None,
            "feed_url": None,
            "subtitle": None,
            "author": {"name": None, "uri": None},
            "items": [item],
        }))
        self.assertFalse("authors" in json_feed)

    def test_build_feed_model_prefers_link_fallbacks_for_json(self):
        config.load(configfile)
        feed = output.build_feed_model(
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            '<title>JSON Fallbacks</title>'
            '<link href="http://example.com/from-first-link" />'
            '<entry>'
            '<id>tag:example.com,2026:3</id>'
            '<title>Entry</title>'
            '<updated>2026-04-24T12:00:00Z</updated>'
            '<link href="http://example.com/entry" />'
            '</entry>'
            '</feed>'
        )

        self.assertEqual("http://example.com/from-first-link", feed["home_page_url"])
        self.assertEqual("http://example.com/from-first-link/feed.json", feed["feed_url"])

    def test_render_rss_escapes_cdata_terminator_sequences(self):
        rss = output.render_rss({
            "title": "CDATA Feed",
            "subtitle": None,
            "updated": None,
            "rights": None,
            "home_page_url": None,
            "author": {},
            "entries": [{
                "title": "CDATA Item",
                "id": "tag:example.com,2026:cdata",
                "published": None,
                "updated": None,
                "summary": None,
                "content": "safe ]]> break",
                "links": [{"rel": "alternate", "href": "http://example.com/cdata"}],
                "categories": [],
                "author": {},
                "screenshot": None,
                "source": {"title": None, "id": None, "links": [], "screenshot": None},
            }],
        })

        # Must remain parseable XML and preserve the payload string.
        doc = minidom.parseString(rss)
        item = doc.getElementsByTagName("item")[0]
        description_payload = ''.join(node.nodeValue for node in item.getElementsByTagName("description")[0].childNodes)
        encoded_payload = ''.join(node.nodeValue for node in item.getElementsByTagName("content:encoded")[0].childNodes)
        self.assertEqual(
            "safe ]]> break",
            description_payload)
        self.assertEqual(
            "safe ]]> break",
            encoded_payload)
