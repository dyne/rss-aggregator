#!/usr/bin/env python

import os
import shutil
import tempfile
import unittest
import urllib.parse

import planet
from planet import publish

class PublishTest(unittest.TestCase):

    def setUp(self):
        self.output = tempfile.mkdtemp()
        self.requests = []
        self.urlopen = publish.urllib.request.urlopen
        publish.urllib.request.urlopen = self.capture
        self.original_logger = planet.logger
        planet.getLogger('CRITICAL', None)

    def tearDown(self):
        publish.urllib.request.urlopen = self.urlopen
        planet.logger = self.original_logger
        shutil.rmtree(self.output)

    def capture(self, request):
        self.requests.append(request)

    def touch(self, name):
        path = os.path.join(self.output, name)
        with open(path, 'w') as handle:
            handle.write(name)

    def test_publish_posts_configured_feeds(self):
        self.touch('rss.xml')
        self.touch('feed.json')

        publish.publish(FakeConfig(self.output))

        self.assertEqual(1, len(self.requests))
        request = self.requests[0]
        self.assertEqual('http://hub.example/', request.full_url)
        data = urllib.parse.parse_qs(request.data.decode('utf-8'))
        self.assertEqual(['publish'], data['hub.mode'])
        self.assertEqual(['http://planet.example/rss.xml'], data['hub.url'])

    def test_publish_skips_when_no_matching_feeds(self):
        self.touch('feed.json')
        publish.publish(FakeConfig(self.output))
        self.assertEqual([], self.requests)

class FakeConfig:
    def __init__(self, output):
        self.output = output

    def pubsubhubbub_hub(self):
        return 'http://hub.example/'

    def link(self):
        return 'http://planet.example/'

    def output_dir(self):
        return self.output

    def pubsubhubbub_feeds(self):
        return ['rss.xml']
