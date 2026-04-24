#!/usr/bin/env python

import os, shutil, unittest
from planet import config

workdir = os.path.join('tests', 'work', 'config', 'cache')

class ConfigCsvTest(unittest.TestCase):
    def setUp(self):
        config.load('tests/data/config/rlist-csv.ini')

    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])

    # administrivia

    def test_feeds(self):
        feeds = config.subscriptions()
        feeds.sort()
        self.assertEqual(['feed1', 'feed2'], feeds)

    def test_filter_options(self):
        self.assertEqual(True, config.excerpt('feed1'))
        self.assertEqual(False, config.excerpt('feed2'))
        self.assertEqual('foo', config.regexp('feed1'))
        self.assertEqual('bar', config.regexp('feed2'))
        self.assertEqual('', config.sed('feed1'))
        self.assertEqual('yahoo', config.sed('feed2'))
