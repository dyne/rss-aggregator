import unittest

import src


class FeedParserCompatTest(unittest.TestCase):
    def test_gr_original_ids_extracts_known_attribute(self):
        xml = (
            '<feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:gr="http://www.google.com/schemas/reader/atom/">'
            '<entry><id gr:original-id="http://example.com/2">http://example.com/1</id></entry>'
            '</feed>'
        )
        self.assertEqual(['http://example.com/2'], src._gr_original_ids(xml))

    def test_gr_original_ids_skips_doctype_and_entity_inputs(self):
        doctype_xml = (
            '<!DOCTYPE feed [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            '<feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:gr="http://www.google.com/schemas/reader/atom/">'
            '<entry><id gr:original-id="http://example.com/2">http://example.com/1</id></entry>'
            '</feed>'
        )
        self.assertEqual([], src._gr_original_ids(doctype_xml))
