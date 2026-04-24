#!/usr/bin/env python

import unittest, os, shutil
from planet import config, opml
from os.path import split
from glob import glob
from configparser import ConfigParser

workdir = os.path.join('tests', 'work', 'config', 'cache')

class ReadingListTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/rlist.ini')

    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])

    # administrivia

    def test_feeds(self):
        feeds = [split(feed)[1] for feed in config.subscriptions()]
        feeds.sort()
        self.assertEqual(['testfeed0.atom', 'testfeed1a.atom',
            'testfeed2.atom', 'testfeed3.rss'], feeds)

    # dictionaries

    def test_feed_options(self):
        feeds = dict([(split(feed)[1],feed) for feed in config.subscriptions()])
        feed1 = feeds['testfeed1a.atom']
        self.assertEqual('one', config.feed_options(feed1)['name'])

        feed2 = feeds['testfeed2.atom']
        self.assertEqual('two', config.feed_options(feed2)['name'])

    # dictionaries

    def test_cache(self):
        cache = glob(os.path.join(workdir,'lists','*'))
        self.assertEqual(1,len(cache))

        parser = ConfigParser()
        parser.read(cache[0])

        feeds = [split(feed)[1] for feed in parser.sections()]
        feeds.sort()
        self.assertEqual(['opml.xml', 'testfeed0.atom', 'testfeed1a.atom',
            'testfeed2.atom', 'testfeed3.rss'], feeds)

    def test_only_supported_reading_list_types_are_detected(self):
        config.parser.add_section('http://example.com/custom')
        config.parser.set('http://example.com/custom', 'content_type',
            'custom.filter')
        self.assertEqual(None,
            config.reading_list_type('http://example.com/custom'))
        self.assertTrue(
            'http://example.com/custom' not in config.reading_lists())
