"""Built-in entry filtering for the maintained config surface."""

import os
import re
import subprocess
import textwrap
from xml.dom import Node, minidom

import planet

from . import config

ATOM_NS = 'http://www.w3.org/2005/Atom'
PLANET_NS = 'http://planet.intertwingly.net/'
EXCERPT_WIDTH = 500
TEXT_PATTERNS = [
    (re.compile('<id>.*?</id>'), ' '),
    (re.compile('<url>.*?</url>'), ' '),
    (re.compile('<source>.*?</source>'), ' '),
    (re.compile('<updated.*?</updated>'), ' '),
    (re.compile('<published.*?</published>'), ' '),
    (re.compile('<link .*?>'), ' '),
    (re.compile('''<[^>]* alt=['"]([^'"]*)['"].*?>'''), r' \1 '),
    (re.compile('''<[^>]* title=['"]([^'"]*)['"].*?>'''), r' \1 '),
    (re.compile('''<[^>]* label=['"]([^'"]*)['"].*?>'''), r' \1 '),
    (re.compile('''<[^>]* term=['"]([^'"]*)['"].*?>'''), r' \1 '),
    (re.compile('<.*?>'), ' '),
    (re.compile(r'\s+'), ' '),
    (re.compile('&gt;'), '>'),
    (re.compile('&lt;'), '<'),
    (re.compile('&apos;'), "'"),
    (re.compile('&quot;'), '"'),
    (re.compile('&amp;'), '&'),
    (re.compile(r'\s+'), ' '),
]


class _ExcerptCopy:
    """Recursively copy summary/content nodes into a bounded excerpt."""

    def __init__(self, dom, source, target):
        self.dom = dom
        self.full = False
        self.text = []
        self.textlen = 0
        self.wrapper = textwrap.TextWrapper(width=EXCERPT_WIDTH)
        self.copy_children(source, target)

    def copy_children(self, source, target):
        for child in source.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                self.copy_element(child, target)
            elif child.nodeType == Node.TEXT_NODE:
                self.copy_text(child.data, target)
            if self.full:
                break

    def copy_element(self, source, target):
        child = self.dom.createElementNS(source.namespaceURI, source.nodeName)
        target.appendChild(child)
        for i in range(0, source.attributes.length):
            attr = source.attributes.item(i)
            child.setAttributeNS(attr.namespaceURI, attr.name, attr.value)
        self.copy_children(source, child)

    def copy_text(self, source, target):
        if not source.isspace() and source.strip():
            self.text.append(source.strip())
        lines = self.wrapper.wrap(' '.join(self.text))
        if len(lines) == 1:
            target.appendChild(self.dom.createTextNode(source))
            self.textlen = len(lines[0])
        elif lines:
            excerpt = source[:len(lines[0]) - self.textlen] + ' \u2026'
            target.appendChild(self.dom.createTextNode(excerpt))
            self.full = True


def apply_excerpt(doc):
    """Add a default `planet:excerpt` element to one normalized entry."""
    dom = minidom.parseString(doc)
    source = dom.getElementsByTagNameNS(ATOM_NS, 'summary')
    if not source:
        source = dom.getElementsByTagNameNS(ATOM_NS, 'content')
    if source:
        dom.documentElement.setAttribute('xmlns:planet', PLANET_NS)
        excerpt = dom.createElementNS(PLANET_NS, 'planet:excerpt')
        source[0].parentNode.appendChild(excerpt)
        _ExcerptCopy(dom, source[0], excerpt)
    return dom.toxml('utf-8').decode('utf-8')


def apply_regexp(doc, pattern):
    """Keep one entry only when the configured regexp matches its text."""
    data = doc
    for compiled, replacement in TEXT_PATTERNS:
        data = compiled.sub(replacement, data)
    if pattern and not re.search(pattern, data):
        return ''
    return doc


def apply_sed(doc, script_name):
    """Run one maintained sed cleanup script over an entry document."""
    script = config.SED_FILTERS.get(script_name)
    if not script:
        return doc
    script_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'filters', script))
    proc = subprocess.Popen(
        ['sed', '-f', script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True)
    stdout, stderr = proc.communicate(doc)
    if stderr:
        planet.logger.error(stderr)
    return stdout


def apply_filters(feed_uri, doc):
    """Apply the maintained built-in filters in fixed order."""
    if config.regexp(feed_uri):
        doc = apply_regexp(doc, config.regexp(feed_uri))
        if not doc:
            return ''
    if config.sed(feed_uri):
        doc = apply_sed(doc, config.sed(feed_uri))
        if not doc:
            return ''
    if config.excerpt(feed_uri):
        doc = apply_excerpt(doc)
    return doc
