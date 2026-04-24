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
