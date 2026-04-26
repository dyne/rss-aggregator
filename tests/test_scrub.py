#!/usr/bin/env python

import unittest
from src.scrub import scrub
from src import feedparser

class ScrubTest(unittest.TestCase):

    def test_scrub_removes_active_html_payloads(self):
        hostile_feed = '''
        <feed xmlns='http://www.w3.org/2005/Atom'>
          <entry>
            <id>tag:example.com,2026:1</id>
            <title type="html">&lt;a href="javascript:alert(1)" onclick="alert(2)"&gt;x&lt;/a&gt;</title>
            <summary type="html">&lt;img src="data:text/html,&lt;script&gt;alert(1)&lt;/script&gt;" onload="alert(3)" /&gt;</summary>
            <content type="html">&lt;svg onload="alert(4)"&gt;&lt;circle/&gt;&lt;/svg&gt;&lt;p style="background:url(javascript:alert(5))"&gt;x&lt;/p&gt;</content>
          </entry>
        </feed>
        '''

        data = feedparser.parse(hostile_feed)
        scrub('testfeed', data)

        combined = '\n'.join([
            data.entries[0].title_detail.value,
            data.entries[0].summary_detail.value,
            data.entries[0].content[0].value,
        ]).lower()
        self.assertFalse('javascript:' in combined)
        self.assertFalse('onload=' in combined)
        self.assertFalse('onclick=' in combined)
        self.assertFalse('<script' in combined)
        self.assertFalse('data:text/html' in combined)
