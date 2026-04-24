#!/usr/bin/env python
import unittest, os, glob, shutil, time
from planet.spider import filename
from planet import feedparser, config, storage
from planet.expunge import expungeCache
from xml.dom import minidom
import planet

workdir = 'tests/work/expunge/cache'
sourcesdir = 'tests/work/expunge/cache/sources'
testentries = 'tests/data/expunge/test*.entry'
testfeeds = 'tests/data/expunge/test*.atom'
configfile = 'tests/data/expunge/config.ini'

class ExpungeTest(unittest.TestCase):
    def setUp(self):
        # silence errors
        self.original_logger = planet.logger
        planet.getLogger('CRITICAL',None)

        try:
            os.makedirs(workdir)
            os.makedirs(sourcesdir)
        except:
            self.tearDown()
            os.makedirs(workdir)
            os.makedirs(sourcesdir)
             
    def tearDown(self):
        shutil.rmtree(workdir)
        os.removedirs(os.path.split(workdir)[0])
        planet.logger = self.original_logger

    def test_expunge(self):
        config.load(configfile)

        # create test entries in cache with correct timestamp
        for entry in glob.glob(testentries):
            e=minidom.parse(entry)
            e.normalize()
            eid = e.getElementsByTagName('id')
            efile = filename(workdir, eid[0].childNodes[0].nodeValue)
            eupdated = e.getElementsByTagName('updated')[0].childNodes[0].nodeValue
            emtime = time.mktime(feedparser._parse_date_w3dtf(eupdated))
            if not eid or not eupdated: continue
            shutil.copyfile(entry, efile)
            os.utime(efile, (emtime, emtime))
  
        # create test feeds in cache
        sources = config.cache_sources_directory()
        for feed in glob.glob(testfeeds):
                f=minidom.parse(feed)
                f.normalize()
                fid = f.getElementsByTagName('id')
                if not fid: continue
                ffile = filename(sources, fid[0].childNodes[0].nodeValue)
                shutil.copyfile(feed, ffile)

        # verify that exactly nine entries + one source dir were produced
        files = glob.glob(workdir+"/*")
        self.assertEqual(10, len(files))

        # verify that exactly four feeds were produced in source dir
        files = glob.glob(sources+"/*")
        self.assertEqual(4, len(files))

        # expunge...
        expungeCache()

        # verify that five entries and one source dir are left
        files = glob.glob(workdir+"/*")
        self.assertEqual(6, len(files))

        # verify that the right five entries are left
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test1,1') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test2,1') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test3,3') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test4,2') in files)
        self.assertTrue(os.path.join(workdir,
            'bzr.mfd-consult.dk,2007,venus-expunge-test4,3') in files)

    def test_expunge_sqlite_cache(self):
        config.load(configfile)

        sources = config.cache_sources_directory()
        for feed in (
            'tests/data/expunge/testfeed3.atom',
            'tests/data/expunge/testfeed4.atom',
        ):
            document = minidom.parse(feed)
            feed_id = document.getElementsByTagName('id')[0].childNodes[0].nodeValue
            shutil.copyfile(feed, filename(sources, feed_id))

        entries = [
            ('tag:example.com,2026:feed3-new', 'tag:bzr.mfd-consult.dk,2007:venus-expunge-testfeed3', 300),
            ('tag:example.com,2026:feed3-old', 'tag:bzr.mfd-consult.dk,2007:venus-expunge-testfeed3', 200),
            ('tag:example.com,2026:feed4-newest', 'tag:bzr.mfd-consult.dk,2007:venus-expunge-testfeed4', 400),
            ('tag:example.com,2026:feed4-newer', 'tag:bzr.mfd-consult.dk,2007:venus-expunge-testfeed4', 350),
            ('tag:example.com,2026:feed4-old', 'tag:bzr.mfd-consult.dk,2007:venus-expunge-testfeed4', 250),
            ('tag:example.com,2026:unsubbed', 'tag:bzr.mfd-consult.dk,2007:venus-expunge-unsubbed', 500),
        ]

        for entry_id, feed_id, updated_ts in entries:
            entry_key = filename('', entry_id)
            entry_xml = (
                '<entry xmlns="http://www.w3.org/2005/Atom">'
                f'<id>{entry_id}</id>'
                '<updated>2026-04-24T12:00:00Z</updated>'
                f'<source><id>{feed_id}</id></source>'
                '</entry>'
            )
            storage.upsert_entry(entry_key, entry_id, feed_id, updated_ts, entry_xml)
            with open(os.path.join(workdir, entry_key), 'w', encoding='utf-8') as handle:
                handle.write(entry_xml)

        self.assertEqual(6, storage.entries_count())

        expungeCache()

        remaining = [row[0] for row in storage.list_entries_by_recency()]
        self.assertEqual(
            [
                filename('', 'tag:example.com,2026:feed4-newest'),
                filename('', 'tag:example.com,2026:feed4-newer'),
                filename('', 'tag:example.com,2026:feed3-new'),
            ],
            remaining,
        )
        self.assertFalse(os.path.exists(os.path.join(workdir, filename('', 'tag:example.com,2026:feed3-old'))))
        self.assertFalse(os.path.exists(os.path.join(workdir, filename('', 'tag:example.com,2026:feed4-old'))))
        self.assertFalse(os.path.exists(os.path.join(workdir, filename('', 'tag:example.com,2026:unsubbed'))))

    def test_expunge_sqlite_recovers_or_preserves_unknown_source_rows(self):
        config.load(configfile)

        feed = 'tests/data/expunge/testfeed3.atom'
        document = minidom.parse(feed)
        feed_id = document.getElementsByTagName('id')[0].childNodes[0].nodeValue
        shutil.copyfile(feed, filename(config.cache_sources_directory(), feed_id))

        recovered_old = 'tag:example.com,2026:recover-old'
        recovered_new = 'tag:example.com,2026:recover-new'
        malformed = 'tag:example.com,2026:malformed'
        no_source = 'tag:example.com,2026:no-source'

        for entry_id, updated_ts, entry_xml in (
            (
                recovered_old,
                100,
                '<entry xmlns="http://www.w3.org/2005/Atom">'
                f'<id>{recovered_old}</id>'
                f'<source><id>{feed_id}</id></source>'
                '</entry>',
            ),
            (
                recovered_new,
                200,
                '<entry xmlns="http://www.w3.org/2005/Atom">'
                f'<id>{recovered_new}</id>'
                f'<source><id>{feed_id}</id></source>'
                '</entry>',
            ),
            (malformed, 300, '<entry>'),
            (
                no_source,
                250,
                '<entry xmlns="http://www.w3.org/2005/Atom">'
                f'<id>{no_source}</id>'
                '</entry>',
            ),
        ):
            entry_key = filename('', entry_id)
            storage.upsert_entry(entry_key, entry_id, None, updated_ts, entry_xml)
            with open(os.path.join(workdir, entry_key), 'w', encoding='utf-8') as handle:
                handle.write(entry_xml)

        expungeCache()

        remaining = [row[0] for row in storage.list_entries_by_recency()]
        self.assertEqual(
            [
                filename('', malformed),
                filename('', no_source),
                filename('', recovered_new),
            ],
            remaining,
        )
        self.assertFalse(os.path.exists(os.path.join(workdir, filename('', recovered_old))))
        self.assertTrue(os.path.exists(os.path.join(workdir, filename('', malformed))))
        self.assertTrue(os.path.exists(os.path.join(workdir, filename('', no_source))))
