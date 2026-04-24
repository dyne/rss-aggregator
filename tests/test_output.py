#!/usr/bin/env python

import json
import os
import shutil
import unittest
from xml.dom import minidom

from planet import config, output, splice

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
