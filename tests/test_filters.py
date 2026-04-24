#!/usr/bin/env python

import unittest, xml.dom.minidom
from planet import config, filtering, logger

class FilterTests(unittest.TestCase):

    def apply_filters(self, configfile, testfile):
        config.load(configfile)
        return filtering.apply_filters(None, open(testfile).read())

    def test_excerpt_images(self):
        output = self.apply_filters(
            'tests/data/filter/excerpt-images.ini',
            'tests/data/filter/excerpt-images.xml')

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('planet:excerpt')[0]
        images = excerpt.getElementsByTagName('img')
        self.assertEqual(3, len(images))
        self.assertEqual('inner', images[0].getAttribute('src'))

    def test_excerpt_lorem_ipsum(self):
        output = self.apply_filters(
            'tests/data/filter/excerpt-lorem-ipsum.ini',
            'tests/data/filter/excerpt-lorem-ipsum.xml')

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('planet:excerpt')[0]
        self.assertTrue(excerpt.toxml().find(
            'Lorem ipsum dolor sit amet, consectetuer') >= 0)
        self.assertTrue(excerpt.toxml().find('Class aptent  \u2026') >= 0)

    def test_stripAd_yahoo(self):
        output = self.apply_filters(
            'tests/data/filter/stripAd-yahoo.ini',
            'tests/data/filter/stripAd-yahoo.xml')

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('content')[0]
        self.assertEqual('before--after',
            excerpt.firstChild.firstChild.nodeValue)

    def test_regexp_filter(self):
        output = self.apply_filters(
            'tests/data/filter/regexp-sifter.ini',
            'tests/data/filter/category-one.xml')

        self.assertEqual('', output)

        output = self.apply_filters(
            'tests/data/filter/regexp-sifter.ini',
            'tests/data/filter/category-two.xml')

        self.assertNotEqual('', output)

    def test_regexp_filter2(self):
        output = self.apply_filters(
            'tests/data/filter/regexp-sifter2.ini',
            'tests/data/filter/category-one.xml')

        self.assertNotEqual('', output)

        output = self.apply_filters(
            'tests/data/filter/regexp-sifter2.ini',
            'tests/data/filter/category-two.xml')

        self.assertEqual('', output)

try:
    from subprocess import Popen, PIPE

    _no_sed = True
    if _no_sed:
        try:
            # Python 2.5 bug 1704790 workaround (alas, Unix only)
            import subprocess
            if subprocess.getstatusoutput('sed --version')[0]==0: _no_sed = False 
        except:
            pass

    if _no_sed:
        try:
            sed = Popen(['sed','--version'],stdout=PIPE,stderr=PIPE)
            sed.communicate()
            if sed.returncode == 0: _no_sed = False
        except WindowsError:
            pass

    if _no_sed:
        logger.warn("sed is not available => can't test stripAd_yahoo")
        del FilterTests.test_stripAd_yahoo      

except ImportError:
    logger.warn("Popen is not available => can't test standard filters")
    for method in dir(FilterTests):
        if method.startswith('test_'):  delattr(FilterTests,method)
