#!/usr/bin/env python

import unittest, os, glob, calendar, shutil, time, sqlite3
from unittest import mock
from queue import Queue
from src.spider import filename, spiderPlanet, writeCache
from src import feedparser, config
from src import reconstitute
import src as planet

workdir = 'tests/work/spider/cache'
testfeed = 'tests/data/spider/testfeed%s.atom'
configfile = 'tests/data/spider/config.ini'

class SpiderTest(unittest.TestCase):
    def cache_items(self):
        return [path for path in glob.glob(workdir + "/*")
            if os.path.basename(path) != "cache.sqlite3"]

    def setUp(self):
        # silence errors
        self.original_logger = planet.logger
        planet.getLogger('CRITICAL',None)

        try:
             os.makedirs(workdir)
        except:
             self.tearDown()
             os.makedirs(workdir)
    
    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])
        planet.logger = self.original_logger

    def test_filename(self):
        self.assertEqual(os.path.join('.', 'example.com,index.html'),
            filename('.', 'http://example.com/index.html'))
        self.assertEqual(os.path.join('.',
            'planet.intertwingly.net,2006,testfeed1,1'),
            filename('.', 'tag:planet.intertwingly.net,2006:testfeed1,1'))
        self.assertEqual(os.path.join('.',
            '00000000-0000-0000-0000-000000000000'),
            filename('.', 'urn:uuid:00000000-0000-0000-0000-000000000000'))

        # Requires Python 2.3
        try:
            import encodings.idna
        except:
            return
        self.assertEqual(os.path.join('.', 'xn--8ws00zhy3a.com'),
            filename('.', 'http://www.\u8a79\u59c6\u65af.com/'))

    def spiderFeed(self, feed_uri):
        feed_info = feedparser.parse('<feed/>')
        data = feedparser.parse(feed_uri)
        writeCache(feed_uri, feed_info, data)

    def verify_spiderFeed(self):
        files = self.cache_items()
        files.sort()

        # verify that exactly four files + one sources dir were produced
        self.assertEqual(5, len(files))

        # verify that the file names are as expected
        self.assertTrue(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed1,1') in files)

        # verify that the file timestamps match atom:updated
        data = feedparser.parse(files[2])
        self.assertEqual(['application/atom+xml'], [link.type
            for link in data.entries[0].source.links if link.rel=='self'])
        self.assertEqual('one', data.entries[0].source.planet_name)
        self.assertEqual('2006-01-03T00:00:00Z', data.entries[0].updated)
        self.assertEqual(os.stat(files[2]).st_mtime,
            calendar.timegm(data.entries[0].updated_parsed))

    def test_spiderFeed(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1b')
        self.verify_spiderFeed()

    def test_spiderFeed_skips_malformed_entry_and_keeps_processing(self):
        config.load(configfile)
        original = reconstitute.reconstitute
        call_count = {'count': 0}

        def fail_one_entry(data, entry):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise ValueError('bad entry payload')
            return original(data, entry)

        with mock.patch('src.spider.reconstitute.reconstitute', side_effect=fail_one_entry):
            self.spiderFeed(testfeed % '1b')

        # three entries + sources directory remain when one malformed entry is skipped.
        self.assertEqual(4, len(self.cache_items()))

    def test_spiderFeed_sqlite_cache(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1b')
        db_path = os.path.join(workdir, "cache.sqlite3")
        self.assertTrue(os.path.exists(db_path))

        conn = sqlite3.connect(db_path)
        try:
            entries = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            feeds = conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
            self.assertEqual(4, entries)
            self.assertEqual(1, feeds)
        finally:
            conn.close()

    def test_spiderFeed_retroactive_filter(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1b')
        self.assertEqual(5, len(self.cache_items()))
        config.parser.set('Planet', 'regexp', 'two')
        self.spiderFeed(testfeed % '1b')
        self.assertEqual(1, len(self.cache_items()))

    def test_spiderFeed_rewrites_lemmy_entries_to_upstream_metadata(self):
        feed_uri = 'https://fed.dyne.org/feeds/c/cybersec.xml?sort=New'
        config.load(configfile)
        config.parser.add_section(feed_uri)
        config.parser.set(feed_uri, 'name', 'cybersec')
        config.parser.set(feed_uri, 'lemmy', 'true')
        feed_info = feedparser.parse('<feed/>')
        data = feedparser.parse("""\
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
          <channel>
            <title>fed.dyne.org - cybersec</title>
            <link>https://fed.dyne.org/c/cybersec</link>
            <item>
              <title>The Citizen Lab Bad Connection</title>
              <link>https://fed.dyne.org/post/984420</link>
              <guid isPermaLink="true">https://fed.dyne.org/post/984420</guid>
              <pubDate>Fri, 24 Apr 2026 03:06:51 GMT</pubDate>
              <description><![CDATA[<div>submitted by <a href="https://fed.dyne.org/u/jaromil">jaromil</a> to <a href="https://fed.dyne.org/c/cybersec">cybersec</a><br/>8 points | <a href="https://fed.dyne.org/post/984420">0 comments</a><br/><a href="https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/">https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/</a></div>]]></description>
              <author>https://fed.dyne.org/u/jaromil</author>
              <enclosure url="https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/" type="text/html; charset=utf-8" length="0" />
              <media:content medium="image" url="https://fed.dyne.org/pictrs/image/example-cover.png" />
            </item>
          </channel>
        </rss>
        """)
        metadata = {
            'title': 'Bad Connection: Uncovering Global Telecom Exploitation',
            'summary': 'Citizen Lab tracks covert telecom surveillance operations.',
            'image': 'https://citizenlab.ca/assets/cover.png',
        }
        with mock.patch('src.lemmy.media.fetch_page_metadata', return_value=metadata):
            writeCache(feed_uri, feed_info, data)

        files = self.cache_items()
        entry_path = [path for path in files if os.path.basename(path) != 'sources'][0]
        cached = feedparser.parse(entry_path).entries[0]
        self.assertEqual(
            'https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/',
            cached.link,
        )
        self.assertEqual(metadata['title'], cached.title)
        self.assertEqual(metadata['summary'], cached.summary)
        self.assertFalse('submitted by' in cached.summary)
        self.assertEqual('https://citizenlab.ca/assets/cover.png', cached.links[1].href)

    def test_spiderFeed_uses_lemmy_media_content_image_when_upstream_has_none(self):
        feed_uri = 'https://fed.dyne.org/feeds/c/cybersec.xml?sort=New'
        config.load(configfile)
        config.parser.add_section(feed_uri)
        config.parser.set(feed_uri, 'name', 'cybersec')
        config.parser.set(feed_uri, 'lemmy', 'true')
        feed_info = feedparser.parse('<feed/>')
        data = feedparser.parse("""\
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
          <channel>
            <title>fed.dyne.org - cybersec</title>
            <link>https://fed.dyne.org/c/cybersec</link>
            <item>
              <title>The Citizen Lab Bad Connection</title>
              <link>https://fed.dyne.org/post/984420</link>
              <guid isPermaLink="true">https://fed.dyne.org/post/984420</guid>
              <pubDate>Fri, 24 Apr 2026 03:06:51 GMT</pubDate>
              <description><![CDATA[<div>submitted by <a href="https://fed.dyne.org/u/jaromil">jaromil</a> to <a href="https://fed.dyne.org/c/cybersec">cybersec</a><br/>8 points | <a href="https://fed.dyne.org/post/984420">0 comments</a><br/><a href="https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/">https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/</a></div>]]></description>
              <media:content medium="image" url="https://fed.dyne.org/pictrs/image/example-cover.png" />
            </item>
          </channel>
        </rss>
        """)
        metadata = {
            'title': 'Bad Connection: Uncovering Global Telecom Exploitation',
            'summary': 'Citizen Lab tracks covert telecom surveillance operations.',
            'image': None,
        }
        with mock.patch('src.lemmy.media.fetch_page_metadata', return_value=metadata):
            writeCache(feed_uri, feed_info, data)

        files = self.cache_items()
        entry_path = [path for path in files if os.path.basename(path) != 'sources'][0]
        cached = feedparser.parse(entry_path).entries[0]
        self.assertEqual('https://fed.dyne.org/pictrs/image/example-cover.png', cached.links[1].href)

    def test_spiderUpdate(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '1a')
        self.spiderFeed(testfeed % '1b')
        self.verify_spiderFeed()

    def test_spiderFeedUpdatedEntries(self):
        config.load(configfile)
        self.spiderFeed(testfeed % '4')
        self.assertEqual(2, len(self.cache_items()))
        data = feedparser.parse(workdir + 
            '/planet.intertwingly.net,2006,testfeed4')
        self.assertEqual('three', data.entries[0].content[0].value)

    def verify_spiderPlanet(self):
        files = self.cache_items()

        # verify that exactly eight files + 1 source dir were produced
        self.assertEqual(14, len(files))

        # verify that the file names are as expected
        self.assertTrue(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed1,1') in files)
        self.assertTrue(os.path.join(workdir,
            'planet.intertwingly.net,2006,testfeed2,1') in files)

        data = feedparser.parse(workdir + 
            '/planet.intertwingly.net,2006,testfeed3,1')
        self.assertEqual(['application/rss+xml'], [link.type
            for link in data.entries[0].source.links if link.rel=='self'])
        self.assertEqual('three', data.entries[0].source.author_detail.name)
        self.assertEqual('three', data.entries[0].source['planet_css-id'])

    def test_spiderPlanet(self):
        config.load(configfile)
        spiderPlanet()
        self.verify_spiderPlanet()

    def test_spiderThreads(self):
        config.load(configfile.replace('config','threaded'))
        _PORT = config.parser.getint('Planet','test_port')

        log = []
        from http.server import SimpleHTTPRequestHandler
        class TestRequestHandler(SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                log.append(args)

        from threading import Thread
        class TestServerThread(Thread):
          def __init__(self):
              self.ready = 0
              self.done = 0
              Thread.__init__(self)
          def run(self):
              from http.server import HTTPServer
              httpd = HTTPServer(('',_PORT), TestRequestHandler)
              self.ready = 1
              while not self.done:
                  httpd.handle_request()

        httpd = TestServerThread()
        httpd.start()
        while not httpd.ready:
            time.sleep(0.1)

        try:
            spiderPlanet()
        finally:
            httpd.done = 1
            import urllib.request, urllib.parse, urllib.error
            urllib.request.urlopen('http://127.0.0.1:%d/' % _PORT).read()

        status = [int(rec[1]) for rec in log if str(rec[0]).startswith('GET ')]
        status.sort()
        self.assertEqual([200,200,200,200,404], status)

        self.verify_spiderPlanet()

    def test_http_thread_marks_oversized_feed_as_413(self):
        class _FakeResponse:
            def __init__(self):
                self.headers = {}

            def read(self, _size):
                from src.spider import MAX_FEED_BYTES
                return b'x' * (MAX_FEED_BYTES + 1)

            def getcode(self):
                return 200

            def close(self):
                return None

        input_queue = Queue()
        output_queue = Queue()
        uri = 'http://example.com/feed.atom'
        input_queue.put((uri, feedparser.parse('<feed/>')))
        input_queue.put((None, None))

        with mock.patch('src.spider.urllib.request.urlopen', return_value=_FakeResponse()):
            from src.spider import httpThread
            httpThread(0, input_queue, output_queue, planet.logger)

        _uri, _feed_info, feed = output_queue.get_nowait()
        self.assertEqual('413', str(feed.headers.status))

    def test_spiderPlanet_records_parse_failure_without_crash(self):
        config.load(configfile)
        uri = 'http://malicious.example/malformed.atom'
        sources_dir = config.cache_sources_directory()
        source_cache_path = filename(sources_dir, uri)
        original_parse = feedparser.parse

        def fake_parse(source, *args, **kwargs):
            if source == uri:
                raise ValueError('malformed feed body')
            return original_parse(source, *args, **kwargs)

        with mock.patch('src.spider.config.subscriptions', return_value=[uri]):
            with mock.patch('src.spider.feedparser.parse', side_effect=fake_parse):
                spiderPlanet()

        source = original_parse(source_cache_path)
        self.assertEqual('internal server error', source.feed.get('planet_message'))
