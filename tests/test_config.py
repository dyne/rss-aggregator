#!/usr/bin/env python

import os
import shutil
import tempfile
import unittest
from src import config

class ConfigTest(unittest.TestCase):
    def tearDown(self):
        workdir = 'tests/work/config'
        if os.path.exists(workdir):
            shutil.rmtree(os.path.split(workdir)[0])

    def setUp(self):
        config.load('tests/data/config/basic.ini')

    def write_config(self, body):
        workdir = 'tests/work/config'
        os.makedirs(workdir, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.ini',
            dir=workdir,
            delete=False,
            encoding='utf-8',
        )
        try:
            handle.write(body)
        finally:
            handle.close()
        return handle.name

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

    def test_items_per_page(self):
        self.assertEqual(50, config.items_per_page())

    # dictionaries

    def test_feed_options(self):
        self.assertEqual('one', config.feed_options('feed1')['name'])
        self.assertEqual('two', config.feed_options('feed2')['name'])

    def test_filter_options(self):
        self.assertEqual(True, config.excerpt('feed1'))
        self.assertEqual(False, config.excerpt('feed2'))
        self.assertEqual('foo', config.regexp('feed1'))
        self.assertEqual('bar', config.regexp('feed2'))
        self.assertEqual('', config.sed('feed1'))
        self.assertEqual('yahoo', config.sed('feed2'))
        self.assertEqual(False, config.lemmy('feed1'))
        self.assertEqual('stripAd/yahoo.sed', config.sed_filter('feed2'))

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
        self.assertEqual(False, config.lemmy('feed1'))
        self.assertEqual('stripAd/yahoo.sed', config.sed_filter('feed1'))
        self.assertEqual('stripAd/feedburner.sed', config.sed_filter('feed2'))

    def test_unknown_sed_name_is_rejected(self):
        config.load('tests/data/config/filter-options.ini')
        config.parser.set('feed2', 'sed', 'unknown')
        self.assertEqual('', config.sed_filter('feed2'))

    def test_planet_level_fallbacks_and_missing_planet_section(self):
        path = self.write_config(
            '[feed-a]\n'
            'name = one\n'
            '\n'
            '[feed-b]\n'
            'name = two\n'
        )
        config.load(path)
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['feed-a', 'feed-b'], feeds)
        self.assertEqual({}, config.planet_options())
        self.assertEqual(None, config.feed())
        self.assertEqual(None, config.feedtype())

        path = self.write_config(
            '[Planet]\n'
            'link = http://example.com/site/\n'
            '\n'
            '[feed-a]\n'
            'name = one\n'
        )
        config.load(path)
        self.assertEqual('http://example.com/site/rss.xml', config.feed())
        self.assertEqual('rss', config.feedtype())

        path = self.write_config(
            '[Planet]\n'
            'link = http://example.com/site/\n'
            'feed = http://example.com/site/atom.xml\n'
        )
        config.load(path)
        self.assertEqual('http://example.com/site/atom.xml', config.feed())
        self.assertEqual(None, config.feedtype())

    def test_sed_and_feed_option_edge_cases(self):
        path = self.write_config(
            '[Planet]\n'
            'custom_value = inherited\n'
            '\n'
            '[feed-a]\n'
            'name = one\n'
            '\n'
            '[feed-b]\n'
            'name = two\n'
            'custom_value = overridden\n'
            'sed = yahoo\n'
        )
        config.load(path)
        self.assertEqual('', config.sed_filter('feed-a'))
        self.assertEqual('stripAd/yahoo.sed', config.sed_filter('feed-b'))
        self.assertEqual('inherited', config.feed_options('feed-a')['custom_value'])
        self.assertEqual('overridden', config.feed_options('feed-b')['custom_value'])

    def test_excerpt_boolean_parsing_uses_supported_spellings(self):
        path = self.write_config(
            '[Planet]\n'
            '\n'
            '[feed-true]\n'
            'excerpt = yes\n'
            '\n'
            '[feed-one]\n'
            'excerpt = 1\n'
            '\n'
            '[feed-on]\n'
            'excerpt = on\n'
            '\n'
            '[feed-false]\n'
            'excerpt = false\n'
            '\n'
            '[feed-zero]\n'
            'excerpt = 0\n'
            '\n'
            '[feed-off]\n'
            'excerpt = off\n'
        )
        config.load(path)
        self.assertEqual(True, config.excerpt('feed-true'))
        self.assertEqual(True, config.excerpt('feed-one'))
        self.assertEqual(True, config.excerpt('feed-on'))
        self.assertEqual(False, config.excerpt('feed-false'))
        self.assertEqual(False, config.excerpt('feed-zero'))
        self.assertEqual(False, config.excerpt('feed-off'))

    def test_lemmy_boolean_parsing_uses_supported_spellings(self):
        path = self.write_config(
            '[Planet]\n'
            'lemmy = yes\n'
            '\n'
            '[feed-one]\n'
            '\n'
            '[feed-two]\n'
            'lemmy = off\n'
        )
        config.load(path)
        self.assertEqual(True, config.lemmy('feed-one'))
        self.assertEqual(False, config.lemmy('feed-two'))
