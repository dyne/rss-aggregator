## Migration from older Planet and Venus setups

Current Venus keeps the feed aggregation model, but simplifies the output surface. Existing users should plan around the following changes:

- You will need to start over with a new cache directory as the format of the cache has changed dramatically.
- Template and theme settings such as `output_theme`, `template_files`, and `template_directories` are gone.
- Venus now writes built-in `news.xml`, `news-index.json`, and numbered `news/*.json` files into `output_dir`.
- Old theme files, `.tmpl` files, and Django or Genshi output templates are no longer part of the maintained product.
- Venus now requires Python 3.9 or newer.
- Generic filter lists and per-filter sections are gone. Migrate filtering to the built-in `excerpt`, `regexp`, and `sed` options.

Clients that previously read `feed.json` should migrate to `news-index.json` first, then request only the numbered `news/{n}.json` entries they need. Numbered files are newest-first and can shift between runs when fresher entries arrive.

When migrating a config, keep feed subscriptions, cache settings, normalization overrides, and any built-in filter settings you still need. Remove theme sections and any old `filters = ...` or `filter_directories` configuration. After that, review [configuration](config.md) and [output files](output.md) for the maintained behavior.
