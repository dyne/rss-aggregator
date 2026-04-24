#!/usr/bin/env python

import os
import re
import unittest
from glob import glob

DOC_LINK = re.compile(r'\[[^\]]+\]\(([^)]+)\)')


class DocsTest(unittest.TestCase):

    def test_docs_are_markdown(self):
        docs = sorted(os.path.basename(doc) for doc in glob('docs/*.md'))
        self.assertEqual([
            'config.md',
            'contributing.md',
            'etiquette.md',
            'filters.md',
            'index.md',
            'installation.md',
            'migration.md',
            'normalization.md',
            'output.md',
        ], docs)
        self.assertEqual([], glob('docs/*.html'))

    def test_local_markdown_links_resolve(self):
        for doc in glob('docs/*.md'):
            source = open(doc, encoding='utf-8').read()
            for target in DOC_LINK.findall(source):
                if target.startswith(('http://', 'https://', 'mailto:')):
                    continue

                path = target.split('#', 1)[0]
                if not path:
                    continue

                self.assertFalse(path.endswith('.html'),
                    'Unexpected html link in %s: %s' % (doc, target))

                resolved = os.path.normpath(
                    os.path.join(os.path.dirname(doc), path))
                self.assertTrue(os.path.exists(resolved),
                    'Broken local link in %s: %s' % (doc, target))
