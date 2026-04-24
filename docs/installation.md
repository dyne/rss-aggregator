## Installation

Venus has been tested on Linux, macOS, and Windows.

You'll need Python 3.9 or newer installed on your system.

Install the locked Python dependencies from the checkout with uv:

>     uv sync

The maintained runtime has one supported command, `planet.py`. It reads one
local INI file, fetches feeds, writes `rss.xml` plus `feed.json`, and exits.
List subscriptions directly in that file; the maintained runtime does not load
OPML, CSV, or remote config sources. It does not require optional template
engines or XSLT tooling. If you use the built-in `sed` cleanup option, make
sure your system `sed` command is available.

### General Instructions

These instructions apply to any platform. Check the instructions below for more specific instructions for your platform.

1.  If you are reading this online, you will need to [download](../README.md) and extract the files into a folder somewhere. You can place this wherever you like, `~/planet` and `~/venus` are good choices, but so's anywhere else you prefer.

2.  This is very important: from within that directory, type the following command:

    > `uv run python runtests.py`

    This should take anywhere from a one to ten seconds to execute. No network connection is required, and the script cleans up after itself. If the script completes with an "OK", you are good to go. Otherwise stopping here and inquiring on the [mailing list](http://lists.planetplanet.org/mailman/listinfo/devel) is a good idea as it can save you lots of frustration down the road.

3.  Make a copy of one of the `ini` the files in the [examples](../examples) subdirectory, and put it wherever you like; I like to use the Planet's name (so `~/planet/debian`), but it's really up to you.

4.  Edit the `config.ini` file in this directory to taste, it's pretty well documented so you shouldn't have any problems here. Pay particular attention to the `output_dir` option, which should be readable by your web server. Venus will write `rss.xml` and `feed.json` there. If the directory you specify in your `cache_dir` exists; make sure that it is empty.

5.  Run it: `uv run python planet.py pathto/config.ini`

    You'll want to add this to cron, make sure you run it from the right directory.

6.  (Optional)

    Tell us about it! We'd love to link to you on planetplanet.org :-)
