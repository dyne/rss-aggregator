# Dyne/RSS-Aggregator

Formerly known as "Planet" or "Venus", this is a flexible feed aggregator. It
downloads news feeds published by web sites and aggregates their content
together into a single combined feed, latest news first.  This version of
Planet was named Venus and is now Dyne/RSS-Aggregator as it is the third major
version, after its second version was widely used at Dyne.org.

It uses the maintained Universal Feed Parser package to read CDF, RDF, RSS,
and Atom feeds, html5lib to normalize markup, and either Tomas Styblo's
templating engine or an optional XSLT backend to output static files in any
format you can dream up.

RSS-Aggregator runs on Python 3. Install the runtime dependencies from the
checkout with:
```
  python3 -m pip install -e .
```
Run the test suite with:
```
  python3 runtests.py
```
To get started, check out the documentation in the docs directory.  If you have
any questions or comments, please don't hesitate to use Github or our channels:
https://dyne.org/contact

