# Dyne/RSS-Aggregator

Formerly known as "Planet" or "Venus", this is a feed aggregator. It downloads
news feeds published by web sites and aggregates their content together into a
single combined feed, latest news first. This version of Planet was named
Venus and is now Dyne/RSS-Aggregator as it is the third major version, after
its second version was widely used at Dyne.org.

It uses the maintained Universal Feed Parser package to read CDF, RDF, RSS,
and Atom feeds, html5lib to normalize markup, and writes two built-in output
files: `rss.xml` for syndication and `feed.json` for application use. When
feeds expose site images, or the source page publishes Open Graph image
metadata, Venus includes that screenshot metadata in the aggregate output.

RSS-Aggregator runs on Python 3. Install the locked runtime dependencies from
the checkout with uv:
```
  uv sync
```
Run the test suite with:
```
  uv run pytest
```
Generate a coverage report with:
```
  uv run pytest --cov=src --cov-report=term-missing --cov-report=xml
```
Run the aggregator with:
```
  uv run python planet.py pathto/config.ini
```

Build and smoke-test the packaged CLI with:
```
  uv build
  uvx --from ./dist/rss_aggregator-3.0.0-py3-none-any.whl rss-aggregator --help
```

`planet.py` remains the maintained in-tree CLI entrypoint. Packaged installs
also expose the same `main()` via the `rss-aggregator` console script. Both
commands read one local INI configuration with direct feed sections, fetch
feeds, write `rss.xml` plus `feed.json`, and exit. The maintained runtime does
not support hub publish, reading-list ingestion, or a separate moderation
workflow.

To get started, check out the documentation in the docs directory.  If you have
any questions or comments, please don't hesitate to use Github or our channels:
https://dyne.org/contact
