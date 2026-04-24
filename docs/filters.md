## Filters

Venus keeps filtering as a small built-in part of feed configuration. Entries are filtered while a feed is fetched and normalized, before they are written to the cache and before `rss.xml` or `feed.json` are generated.

Filters operate on individual normalized entries, not on final output files.

Input to a filter is an aggressively [normalized](normalization.md) entry. For example, if a feed is RSS 1.0 with 10 items, the filter will be called ten times, each with a single Atom 1.0 entry, with all text constructs expressed as XHTML, and everything encoded as UTF-8.

The maintained filtering contract has three options:

`excerpt = true`  
Adds a built-in `planet:excerpt` element to each kept entry. See [opml-top100.ini](../examples/opml-top100.ini) for a minimal planet-wide example.

`regexp = ...`  
Keeps only entries whose normalized text matches the given regular expression. This is backed by the maintained [regexp helper](../filters/regexp_sifter.py), but the config surface is the built-in `regexp` option rather than `filters=...`.

`sed = ...`  
Runs one built-in cleanup script from [the stripAd directory](../filters/stripAd/). Supported values are `feedburner`, `google_ad_map`, and `yahoo`.

### Notes

- Planet-level values apply to every feed; feed-level values override them for one subscription.
- Entries are processed in a fixed order: `regexp`, then `sed`, then `excerpt`.
- If a filter step produces no output, the entry is not written to the cache or processed further.
- Changing filter configuration does not rewrite old cache entries by itself. Run Venus again so the affected feeds are fetched and cached with the new settings.
