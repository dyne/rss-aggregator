#!/usr/bin/env python

import unittest, xml.dom.minidom
from planet import shell, config, logger

class FilterTests(unittest.TestCase):

    def test_excerpt_images(self):
        config.load('tests/data/filter/excerpt-images.ini')
        testfile = 'tests/data/filter/excerpt-images.xml'
        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('planet:excerpt')[0]
        images = excerpt.getElementsByTagName('img')
        self.assertEqual(3, len(images))
        self.assertEqual('inner', images[0].getAttribute('src'))

    def test_excerpt_lorem_ipsum(self):
        testfile = 'tests/data/filter/excerpt-lorem-ipsum.xml'
        config.load('tests/data/filter/excerpt-lorem-ipsum.ini')

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('planet:excerpt')[0]
        self.assertTrue(excerpt.toxml().find(
            'Lorem ipsum dolor sit amet, consectetuer') >= 0)
        self.assertTrue(excerpt.toxml().find('Class aptent  \u2026') >= 0)

    def test_stripAd_yahoo(self):
        testfile = 'tests/data/filter/stripAd-yahoo.xml'
        config.load('tests/data/filter/stripAd-yahoo.ini')

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        dom = xml.dom.minidom.parseString(output)
        excerpt = dom.getElementsByTagName('content')[0]
        self.assertEqual('before--after',
            excerpt.firstChild.firstChild.nodeValue)

    def test_regexp_filter(self):
        config.load('tests/data/filter/regexp-sifter.ini')

        testfile = 'tests/data/filter/category-one.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertEqual('', output)

        testfile = 'tests/data/filter/category-two.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertNotEqual('', output)

    def test_regexp_filter2(self):
        config.load('tests/data/filter/regexp-sifter2.ini')

        testfile = 'tests/data/filter/category-one.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertNotEqual('', output)

        testfile = 'tests/data/filter/category-two.xml'

        output = open(testfile).read()
        for filter in config.filters():
            output = shell.run(filter, output, mode="filter")

        self.assertEqual('', output)

    def test_unsupported_filter_type_is_rejected(self):
        testfile = 'tests/data/filter/index.html'
        self.assertEqual(None,
            shell.run('unsupported.tmpl', open(testfile).read(), mode="filter"))

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
