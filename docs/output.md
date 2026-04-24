## Output Files

Venus writes two built-in files into `output_dir` on every successful run:

`rss.xml`  
The aggregated RSS feed. This is the canonical syndication output.

`feed.json`  
A JSON Feed style document for applications and downstream tooling. It includes item attachments, source metadata, and screenshots when available.

No additional publish step runs after these files are written. A `planet.py`
run finishes once the built-in outputs have been generated.

### What metadata is preserved

The built-in writers preserve the normalized aggregate feed title, link, owner metadata, entry titles, summaries, content, links, categories, authors, enclosures, and source information. Venus also carries source screenshots when they can be derived from feed metadata such as `logo` or `icon`, or from a limited Open Graph lookup of the source page.

### No theme selection

Older Venus releases could render multiple themed outputs through template engines. The maintained output model is now fixed: one RSS file and one JSON file. Output customization happens by changing normalized feed data through the built-in filtering options, not by choosing a theme.
