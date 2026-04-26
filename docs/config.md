## Configuration

Configuration files are in [ConfigParser](https://docs.python.org/3/library/configparser.html) format which basically means the same format as INI files, i.e., they consist of a series of `[sections]`, in square brackets, with each section containing a list of `name:value` pairs (or `name=value` pairs, if you prefer).

You are welcome to place your entire configuration into one file. The
maintained runtime reads only the local INI files you pass to `planet.py` or
`rss-aggregator`;
it does not fetch or expand OPML, CSV, or remote subscription lists.

### `[planet]`

This is the only required section, which is a bit odd as none of the parameters listed below are required. Even so, you really do want to provide many of these, especially ones that identify your planet and set `output_dir`.

Below is the maintained set of built-in planet configuration parameters.

> name  
> Your planet's name
>
> link  
> Link to the main page
>
> owner_name  
> Your name
>
> owner_email  
> Your e-mail address
>
> <!-- -->
>
> cache_directory  
> Where cached feeds are stored
>
> output_dir  
> Directory where Venus writes `rss.xml` and `feed.json`
>
> <!-- -->
>
> excerpt  
> Boolean toggle that adds a built-in `planet:excerpt` element to each cached entry
>
> regexp  
> Regular expression that must match the normalized entry text for the entry to be kept
>
> sed  
> Short name of one built-in cleanup script from `filters/stripAd/`. The maintained values are `feedburner`, `google_ad_map`, and `yahoo`.
>
> lemmy  
> Boolean toggle that rewrites Lemmy wrapper posts to the first upstream article link and fills the entry from the upstream page metadata.
>
> <!-- -->
>
> items_per_page  
> How many items to include in the built-in output files
>
> ~~days_per_page~~  
> How many complete days of posts to put on each page This is the absolute, hard limit (over the item limit)
>
> date_format  
> [strftime](http://docs.python.org/lib/module-time.html#l2h-2816) format used for date rendering in log and legacy helper paths
>
> new_date_format  
> [strftime](http://docs.python.org/lib/module-time.html#l2h-2816) format kept for compatibility with legacy helper code
>
> ~~encoding~~  
> Output encoding for the file. The special "xml" value outputs ASCII with XML character references
>
> ~~locale~~  
> Locale to use for (e.g.) strings in dates, default is taken from your system
>
> activity_threshold  
> If non-zero, all feeds which have not been updated in the indicated number of days will be marked as inactive
>
> <!-- -->
>
> log_level  
> One of `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`
>
> <u>log_format</u>  
> [format string](http://docs.python.org/lib/node422.html) to use for logging output. Note: this configuration value is processed [raw](http://docs.python.org/lib/ConfigParser-objects.html)
>
> feed_timeout  
> Number of seconds to wait for any given feed
>
> new_feed_items  
> Maximum number of items to include in the output from any one feed
>
> spider_threads  
> The number of threads to use when spidering. When set to 0, the default, no threads are used and spidering follows the traditional algorithm.
>
> http_cache_directory  
> If `spider_threads` is specified, you can also specify a directory to be used for an additional HTTP cache to front end the Venus cache. If specified as a relative path, it is evaluated relative to the `cache_directory`.
>
> cache_keep_entries  
> Used by `expunge` to determine how many entries should be kept for each source when expunging old entries from the cache directory. This may be overriden on a per subscription feed basis.
>
> Additional options can be found in [normalization level overrides](normalization.md#overrides).

### `[DEFAULT]`

Values placed in this section are used as default values for all sections. While it is true that few values make sense in all sections; in most cases unused parameters cause few problems.

### `[`*subscription*`]`

All sections other than `planet` or `DEFAULT` are treated as subscriptions and
typically take the form of a URI.

The most common options here are `name`, content and normalization overrides, and the built-in filtering options `excerpt`, `regexp`, `sed`, and `lemmy`.

[Normalization overrides](normalization.md#overrides) can also be defined here.

### Built-in filtering

Filtering is part of the maintained configuration surface and does not use separate filter sections. Planet-level values apply to every feed unless a subscription overrides them.

When more than one built-in option is enabled, Venus applies them in this fixed order:

1.  `regexp`
2.  `sed`
3.  `excerpt`

See [Filters](filters.md) for the behavioral details and examples.
