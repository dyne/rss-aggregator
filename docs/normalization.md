## Normalization

Venus builds on, and extends, the [Universal Feed Parser](http://www.feedparser.org/) and [html5lib](http://code.google.com/p/html5lib/) to convert all feeds into Atom 1.0, with well formed XHTML, and encoded as UTF-8, meaning that you don't have to worry about funky feeds, tag soup, or character encoding.

### Encoding

Input data in feeds may be encoded in a variety of formats, most commonly ASCII, ISO-8859-1, WIN-1252, AND UTF-8. Additionally, many feeds make use of the wide range of [character entity references](http://www.w3.org/TR/html401/sgml/entities.html) provided by HTML. Each is converted to UTF-8, an encoding which is a proper superset of ASCII, supports the entire range of Unicode characters, and is one of [only two](http://www.w3.org/TR/2006/REC-xml-20060816/#charsets) encodings required to be supported by all conformant XML processors.

Encoding problems are one of the more common feed errors, and every attempt is made to correct common errors, such as the inclusion of the so-called [moronic](http://www.fourmilab.ch/webtools/demoroniser/) versions of smart-quotes. In rare cases where individual characters can not be converted to valid UTF-8 or into [characters allowed in XML 1.0 documents](http://www.w3.org/TR/xml/#charsets), such characters will be replaced with the Unicode [Replacement character](http://www.fileformat.info/info/unicode/char/fffd/index.htm), with a title that describes the original character whenever possible.

Venus uses Python 3 Unicode handling and html5lib to support a wide range of input encodings.

### HTML

A number of different normalizations of HTML are performed. For starters, the HTML is [sanitized](http://www.feedparser.org/docs/html-sanitization.html), meaning that HTML tags and attributes that could introduce javascript or other security risks are removed.

Then, [relative links are resolved](http://www.feedparser.org/docs/resolving-relative-links.html) within the HTML. This is also done for links in other areas in the feed too.

Finally, unmatched tags are closed. This is done with a [knowledge of the semantics of HTML](http://code.google.com/p/html5lib/). Additionally, a [large subset of MathML](http://golem.ph.utexas.edu/~distler/blog/archives/000165.html#sanitizespec), as well as a [tiny profile of SVG](http://www.w3.org/TR/SVGMobile/) is also supported.

### Atom 1.0

The Universal Feed Parser also [normalizes the content of feeds](http://www.feedparser.org/docs/content-normalization.html). This involves a [large number of elements](http://www.feedparser.org/docs/reference.html); the best place to start is to look at [annotated examples](http://www.feedparser.org/docs/annotated-examples.html). Among other things a wide variety of [date formats](http://www.feedparser.org/docs/date-parsing.html) are converted into [RFC 3339](http://www.ietf.org/rfc/rfc3339.txt) formatted dates.

If no [ids](http://www.feedparser.org/docs/reference-entry-id.html) are found in entries, attempts are made to synthesize one using (in order):

- [link](http://www.feedparser.org/docs/reference-entry-link.html)
- [title](http://www.feedparser.org/docs/reference-entry-title.html)
- [summary](http://www.feedparser.org/docs/reference-entry-summary.html)
- [content](http://www.feedparser.org/docs/reference-entry-content.html)

If no [updated](http://www.feedparser.org/docs/reference-feed-updated.html) dates are found in an entry, the updated date from the feed is used. If no updated date is found in either the feed or the entry, the current time is substituted.
