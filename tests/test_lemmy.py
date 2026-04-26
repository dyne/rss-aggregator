#!/usr/bin/env python

import unittest

from src import feedparser
from src import lemmy


LEMMY_ENTRY_XML = """\
<entry xmlns="http://www.w3.org/2005/Atom">
  <title>The Citizen Lab Bad Connection</title>
  <link rel="alternate" href="https://fed.dyne.org/post/984420" />
  <link rel="enclosure" href="https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/" type="text/html; charset=utf-8" />
  <id>https://fed.dyne.org/post/984420</id>
  <summary type="html">&lt;div&gt;submitted by &lt;a href="https://fed.dyne.org/u/jaromil"&gt;jaromil&lt;/a&gt; to &lt;a href="https://fed.dyne.org/c/cybersec"&gt;cybersec&lt;/a&gt;&lt;br/&gt;8 points | &lt;a href="https://fed.dyne.org/post/984420"&gt;0 comments&lt;/a&gt;&lt;br/&gt;&lt;a href="https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/"&gt;https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/&lt;/a&gt;&lt;/div&gt;</summary>
  <author>
    <name>jaromil</name>
  </author>
</entry>
"""

LEMMY_ENTRY_WITH_MEDIA_XML = """\
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>fed.dyne.org - cybersec</title>
    <link>https://fed.dyne.org/c/cybersec</link>
    <item>
      <title>The Citizen Lab Bad Connection</title>
      <link>https://fed.dyne.org/post/984420</link>
      <guid isPermaLink="true">https://fed.dyne.org/post/984420</guid>
      <description><![CDATA[<div>submitted by <a href="https://fed.dyne.org/u/jaromil">jaromil</a> to <a href="https://fed.dyne.org/c/cybersec">cybersec</a><br/>8 points | <a href="https://fed.dyne.org/post/984420">0 comments</a><br/><a href="https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/">https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/</a></div>]]></description>
      <media:content medium="image" url="https://fed.dyne.org/pictrs/image/example-cover.png" />
    </item>
  </channel>
</rss>
"""


class LemmyTest(unittest.TestCase):
    def parse_entry(self):
        return feedparser.parse(LEMMY_ENTRY_XML).entries[0]

    def parse_media_entry(self):
        return feedparser.parse(LEMMY_ENTRY_WITH_MEDIA_XML).entries[0]

    def test_first_upstream_link_skips_lemmy_wrapper_links(self):
        entry = self.parse_entry()
        safe = lambda url: url.startswith('https://')
        self.assertEqual(
            'https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/',
            lemmy.first_upstream_link(entry, safe_url=safe),
        )

    def test_rewrite_entry_replaces_wrapper_with_upstream_metadata(self):
        entry = self.parse_entry()
        metadata = {
            'title': 'Bad Connection: Uncovering Global Telecom Exploitation',
            'summary': 'Citizen Lab tracks covert telecom surveillance operations.',
            'image': 'https://citizenlab.ca/assets/cover.png',
        }
        rewritten = lemmy.rewrite_entry(entry, metadata_fetcher=lambda _url: metadata)
        self.assertTrue(rewritten)
        self.assertEqual(
            'https://citizenlab.ca/research/uncovering-global-telecom-exploitation-by-covert-surveillance-actors/',
            entry.link,
        )
        self.assertEqual(entry.link, entry.id)
        self.assertEqual(metadata['title'], entry.title)
        self.assertEqual(metadata['summary'], entry.summary)
        self.assertFalse('content' in entry)
        self.assertFalse('author' in entry)
        self.assertEqual('https://citizenlab.ca/assets/cover.png', entry.links[1]['href'])

    def test_rewrite_entry_uses_lemmy_media_content_image_when_upstream_has_none(self):
        entry = self.parse_media_entry()
        metadata = {
            'title': 'Bad Connection: Uncovering Global Telecom Exploitation',
            'summary': 'Citizen Lab tracks covert telecom surveillance operations.',
            'image': None,
        }
        rewritten = lemmy.rewrite_entry(entry, metadata_fetcher=lambda _url: metadata)
        self.assertTrue(rewritten)
        self.assertEqual('https://fed.dyne.org/pictrs/image/example-cover.png', entry.links[1]['href'])
