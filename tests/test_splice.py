#!/usr/bin/env python

import unittest
from unittest import mock
from src.splice import splice, config

configfile = 'tests/data/splice/config.ini'

class SpliceTest(unittest.TestCase):

    def test_splice(self):
        config.load(configfile)
        doc = splice()
        self.assertEqual(12,len(doc.getElementsByTagName('entry')))
        self.assertEqual(4,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(16,len(doc.getElementsByTagName('planet:name')))

        self.assertEqual('test planet',
            doc.getElementsByTagName('title')[0].firstChild.nodeValue)

    def test_splice_unsub(self):
        config.load(configfile)
        config.parser.remove_section('tests/data/spider/testfeed2.atom')
        doc = splice()
        self.assertEqual(8,len(doc.getElementsByTagName('entry')))
        self.assertEqual(3,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(11,len(doc.getElementsByTagName('planet:name')))

    def test_splice_new_feed_items(self):
        config.load(configfile)
        config.parser.set('Planet','new_feed_items','3')
        doc = splice()
        self.assertEqual(9,len(doc.getElementsByTagName('entry')))
        self.assertEqual(4,len(doc.getElementsByTagName('planet:source')))
        self.assertEqual(13,len(doc.getElementsByTagName('planet:name')))

    def test_splice_skips_corrupt_cached_sqlite_entry(self):
        config.load(configfile)
        with mock.patch('src.splice.storage.list_entries_by_recency', return_value=[
            ('broken-entry', None, None, 0, '<entry><broken'),
        ]):
            doc = splice()
        self.assertEqual(0, len(doc.getElementsByTagName('entry')))
