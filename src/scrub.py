"""
Process a set of configuration defined sanitations on a given feed.
"""

from src import feedparser

def scrub(feed_uri, data):
    # resolve relative URIs and sanitize
    for entry in data.entries + [data.feed]:
        for key in entry.keys():
            if key == 'content'and 'content_detail' not in entry:
                node = entry.content[0]
            elif key.endswith('_detail'):
                node = entry[key]
            else:
                continue

            if 'type' not in node: continue
            if not 'html' in node['type']: continue
            if 'value' not in node: continue

            if 'base' in node:
                if hasattr(feedparser, '_resolveRelativeURIs'):
                    node['value'] = feedparser._resolveRelativeURIs(
                        node.value, node.base, 'utf-8', node.type)

            # Run this through HTML5's sanitizer
            doc = None
            if 'xhtml' in node['type']:
              try:
                from xml.dom import minidom
                doc = minidom.parseString(node['value'])
              except:
                node['type']='text/html'

            if not doc:
              from html5lib import html5parser, treebuilders
              p=html5parser.HTMLParser(tree=treebuilders.getTreeBuilder('dom'))
              doc = p.parseFragment(node['value'])

            from html5lib import treewalkers, serializer
            from html5lib.filters import sanitizer
            walker = sanitizer.Filter(treewalkers.getTreeWalker('dom')(doc))
            xhtml = serializer.HTMLSerializer(
                inject_meta_charset=False,
                omit_optional_tags=False,
                quote_attr_values='always',
                use_trailing_solidus=True)
            tree = xhtml.serialize(walker)

            node['value'] = ''.join([str(token) for token in tree])
