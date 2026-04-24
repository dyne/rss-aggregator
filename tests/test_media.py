#!/usr/bin/env python

import os
import shutil
import unittest

from planet import media


WORKDIR = 'tests/work/media'


class MediaTest(unittest.TestCase):
    def tearDown(self):
        if os.path.exists(WORKDIR):
            shutil.rmtree(os.path.split(WORKDIR)[0])

    def test_first_image_from_html(self):
        value = '<p>hello <img src="cover.png" /></p>'
        self.assertEqual('http://example.com/cover.png',
            media.first_image_from_html(value, 'http://example.com/post'))

    def test_fetch_open_graph_image_from_file(self):
        os.makedirs(WORKDIR)
        path = os.path.join(WORKDIR, 'page.html')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(
                '<html><head>'
                '<meta property="og:image" content="shots/site.png" />'
                '</head><body></body></html>')

        file_url = 'file://' + os.path.abspath(path)
        self.assertEqual(
            'file://' + os.path.abspath(os.path.join(WORKDIR, 'shots', 'site.png')),
            media.fetch_open_graph_image(file_url))

    def test_feed_screenshot_prefers_feed_metadata_over_cache(self):
        feed = {
            'logo': 'http://example.com/logo.png',
            'links': [{'rel': 'alternate', 'href': 'http://example.com/'}],
        }
        self.assertEqual(
            'http://example.com/logo.png',
            media.feed_screenshot(
                feed,
                cached='http://example.com/cached.png',
                cached_homepage='http://example.com/'))

    def test_feed_screenshot_reuses_cached_value_when_homepage_is_unchanged(self):
        calls = []
        original = media.fetch_open_graph_image
        media.fetch_open_graph_image = lambda url: calls.append(url) or 'http://example.com/new.png'
        try:
            self.assertEqual(
                'http://example.com/cached.png',
                media.feed_screenshot(
                    {'links': [{'rel': 'alternate', 'href': 'http://example.com/'}]},
                    cached='http://example.com/cached.png',
                    cached_homepage='http://example.com/'))
        finally:
            media.fetch_open_graph_image = original
        self.assertEqual([], calls)

    def test_feed_screenshot_refreshes_when_homepage_changes(self):
        original = media.fetch_open_graph_image
        media.fetch_open_graph_image = lambda url: 'http://example.net/new.png'
        try:
            self.assertEqual(
                'http://example.net/new.png',
                media.feed_screenshot(
                    {'links': [{'rel': 'alternate', 'href': 'http://example.net/'}]},
                    cached='http://example.com/cached.png',
                    cached_homepage='http://example.com/'))
        finally:
            media.fetch_open_graph_image = original

    def test_entry_screenshot_prefers_image_enclosure(self):
        entry = {
            'links': [
                {'rel': 'enclosure', 'href': 'http://example.com/cover.jpg', 'type': 'image/jpeg'},
            ],
            'content_detail': {'value': '<img src="inline.png" />', 'base': 'http://example.com/post'},
        }
        source = {'planet_screenshot': 'http://example.com/source.png'}
        self.assertEqual('http://example.com/cover.jpg',
            media.entry_screenshot(entry, source))

    def test_entry_screenshot_falls_back_to_inline_html_then_source(self):
        entry = {
            'links': [],
            'content_detail': {'value': '<p><img src="inline.png" /></p>', 'base': 'http://example.com/post'},
        }
        source = {'planet_screenshot': 'http://example.com/source.png'}
        self.assertEqual('http://example.com/inline.png',
            media.entry_screenshot(entry, source))
        self.assertEqual('http://example.com/source.png',
            media.entry_screenshot({'links': []}, source))
