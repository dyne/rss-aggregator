#!/usr/bin/env python

import unittest
from planet import config

class ConfigTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/basic.ini')

    def test_feeds(self):
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['feed1', 'feed2'], feeds)

    def test_feed(self):
        self.assertEqual('http://example.com/rss.xml', config.feed())
        self.assertEqual('rss', config.feedtype())

    # planet wide configuration

    def test_name(self):
        self.assertEqual('Test Configuration', config.name())

    def test_link(self):
        self.assertEqual('http://example.com/', config.link())

    def test_pubsubhubbub_hub(self):
        self.assertEqual('http://pubsubhubbub.appspot.com', config.pubsubhubbub_hub())

    def test_items_per_page(self):
        self.assertEqual(50, config.items_per_page())

    # dictionaries

    def test_feed_options(self):
        self.assertEqual('one', config.feed_options('feed1')['name'])
        self.assertEqual('two', config.feed_options('feed2')['name'])

    def test_filters(self):
        self.assertEqual(
            ['regexp_sifter.py?require=bar', 'stripAd/yahoo.sed'],
            config.filters('feed2'))
        self.assertEqual(
            ['regexp_sifter.py?require=foo', 'excerpt.py'],
            config.filters('feed1'))

    # ints

    def test_timeout(self):
        self.assertEqual(30,
            config.feed_timeout())

    def test_filter_option_accessors(self):
        config.load('tests/data/config/filter-options.ini')
        self.assertEqual(True, config.excerpt('feed1'))
        self.assertEqual(False, config.excerpt('feed2'))
        self.assertEqual('planet', config.regexp('feed1'))
        self.assertEqual('mars', config.regexp('feed2'))
        self.assertEqual('yahoo', config.sed('feed1'))
        self.assertEqual('feedburner', config.sed('feed2'))
