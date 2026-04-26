#!/usr/bin/env python

import os
import shutil
import unittest
from unittest import mock

from src import media


WORKDIR = 'tests/work/media'


class MediaTest(unittest.TestCase):
    def tearDown(self):
        if os.path.exists(WORKDIR):
            shutil.rmtree(os.path.split(WORKDIR)[0])

    def test_first_image_from_html(self):
        value = '<p>hello <img src="cover.png" /></p>'
        self.assertEqual('http://example.com/cover.png',
            media.first_image_from_html(value, 'http://example.com/post'))

    def test_safe_public_http_url_allows_public_http_and_https(self):
        def resolver(host, _port):
            if host == 'example.com':
                return [(None, None, None, None, ('93.184.216.34', 0))]
            if host == 'example.org':
                return [(None, None, None, None, ('2606:2800:220:1:248:1893:25c8:1946', 0))]
            return []

        self.assertTrue(media.safe_public_http_url('http://example.com/', resolver=resolver))
        self.assertTrue(media.safe_public_http_url('https://example.org/', resolver=resolver))

    def test_safe_public_http_url_rejects_unsafe_or_malformed_urls(self):
        def resolver(host, _port):
            if host == 'localhost':
                return [(None, None, None, None, ('127.0.0.1', 0))]
            if host == 'internal.example':
                return [(None, None, None, None, ('10.0.1.7', 0))]
            return []

        self.assertFalse(media.safe_public_http_url('file:///tmp/page.html', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('ftp://example.com/', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('http://127.0.0.1/', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('http://[::1]/', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('http://localhost/', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('http://internal.example/', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('http://user:pass@example.com/', resolver=resolver))
        self.assertFalse(media.safe_public_http_url('http:///missing-host', resolver=resolver))

    def test_fetch_open_graph_image_rejects_unsafe_scheme(self):
        with self.assertRaises(ValueError):
            media.fetch_open_graph_image('file:///tmp/page.html')

    def test_fetch_page_metadata_rejects_unsafe_scheme(self):
        with self.assertRaises(ValueError):
            media.fetch_page_metadata('file:///tmp/page.html')

    def test_fetch_page_metadata_reads_title_description_and_image(self):
        response = mock.Mock()
        response.headers.get.return_value = 'text/html; charset=utf-8'
        response.read.side_effect = [
            (
                b'<html><head>'
                b'<title>Fallback title</title>'
                b'<meta property="og:title" content="Open Graph title" />'
                b'<meta name="description" content="Short summary" />'
                b'<meta property="og:image" content="/cover.png" />'
                b'</head><body></body></html>'
            ),
            b'',
        ]
        with mock.patch('urllib.request.urlopen', return_value=response):
            metadata = media.fetch_page_metadata('http://example.com/post')
        self.assertEqual('Open Graph title', metadata['title'])
        self.assertEqual('Short summary', metadata['summary'])
        self.assertEqual('http://example.com/cover.png', metadata['image'])

    def test_fetch_page_metadata_prefers_og_description_over_meta_description(self):
        response = mock.Mock()
        response.headers.get.return_value = 'text/html; charset=utf-8'
        response.read.side_effect = [
            (
                b'<html><head>'
                b'<meta name="description" content="Plain summary" />'
                b'<meta property="og:description" content="Canonical og summary" />'
                b'</head><body></body></html>'
            ),
            b'',
        ]
        with mock.patch('urllib.request.urlopen', return_value=response):
            metadata = media.fetch_page_metadata('http://example.com/post')
        self.assertEqual('Canonical og summary', metadata['summary'])

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

    def test_entry_screenshot_uses_media_content_image_before_html(self):
        entry = {
            'links': [],
            'media_content': [
                {'medium': 'image', 'url': 'http://example.com/media-cover.jpg'},
            ],
            'content_detail': {'value': '<p><img src="inline.png" /></p>', 'base': 'http://example.com/post'},
        }
        self.assertEqual('http://example.com/media-cover.jpg', media.entry_screenshot(entry, {}))

    def test_looks_like_image_uses_mime_and_extension(self):
        self.assertTrue(media.looks_like_image('http://example.com/asset', 'image/webp'))
        self.assertTrue(media.looks_like_image('http://example.com/asset.JPG'))
        self.assertFalse(media.looks_like_image('http://example.com/asset.txt', 'text/plain'))

    def test_source_screenshot_precedence_and_fallback(self):
        self.assertEqual(
            'http://example.com/direct.png',
            media.source_screenshot({
                'screenshot': 'http://example.com/direct.png',
                'planet_screenshot': 'http://example.com/planet.png',
                'logo': 'http://example.com/logo.png',
            }))
        self.assertEqual(
            'http://example.com/planet.png',
            media.source_screenshot({
                'planet_screenshot': 'http://example.com/planet.png',
                'logo': 'http://example.com/logo.png',
                'icon': 'http://example.com/icon.png',
            }))
        self.assertEqual(
            'http://example.com/logo.png',
            media.source_fallback_screenshot({
                'logo': 'http://example.com/logo.png',
                'icon': 'http://example.com/icon.png',
            }))
        self.assertEqual(None, media.source_fallback_screenshot({}))

    def test_should_refresh_screenshot_only_when_homepage_changes(self):
        self.assertFalse(media.should_refresh_screenshot(None, 'http://example.com/'))
        self.assertFalse(media.should_refresh_screenshot('http://example.com/', None))
        self.assertFalse(media.should_refresh_screenshot('http://example.com/', 'http://example.com/'))
        self.assertTrue(media.should_refresh_screenshot('http://example.net/', 'http://example.com/'))

    def test_fetch_open_graph_image_returns_none_for_non_html(self):
        response = mock.Mock()
        response.headers.get.return_value = 'application/json'
        with mock.patch('urllib.request.urlopen', return_value=response):
            self.assertEqual(None, media.fetch_open_graph_image('http://example.com/data.json'))

    def test_feed_screenshot_keeps_cache_for_unsupported_scheme(self):
        with mock.patch.object(media, 'fetch_open_graph_image') as fetch:
            self.assertEqual(
                'http://example.com/cached.png',
                media.feed_screenshot(
                    {'links': [{'rel': 'alternate', 'href': 'ftp://example.com/feed'}]},
                    cached='http://example.com/cached.png',
                    cached_homepage='http://example.com/'))
        fetch.assert_not_called()

    def test_feed_screenshot_keeps_cache_for_private_homepage(self):
        with mock.patch.object(media, 'fetch_open_graph_image') as fetch:
            self.assertEqual(
                'http://example.com/cached.png',
                media.feed_screenshot(
                    {'links': [{'rel': 'alternate', 'href': 'http://127.0.0.1/private'}]},
                    cached='http://example.com/cached.png',
                    cached_homepage='http://example.net/'))
        fetch.assert_not_called()

    def test_feed_screenshot_swallows_fetch_errors(self):
        with mock.patch.object(media, 'fetch_open_graph_image', side_effect=OSError('boom')):
            self.assertEqual(
                'http://example.com/cached.png',
                media.feed_screenshot(
                    {'links': [{'rel': 'alternate', 'href': 'http://example.com/'}]},
                    cached='http://example.com/cached.png',
                    cached_homepage='http://example.net/'))

        with mock.patch.object(media, 'fetch_open_graph_image', side_effect=ValueError('boom')):
            self.assertEqual(
                'http://example.com/cached.png',
                media.feed_screenshot(
                    {'links': [{'rel': 'alternate', 'href': 'http://example.com/'}]},
                    cached='http://example.com/cached.png',
                    cached_homepage='http://example.net/'))
