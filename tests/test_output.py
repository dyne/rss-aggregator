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
