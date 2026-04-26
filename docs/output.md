## Output Files

Venus writes a fixed built-in output set into `output_dir` on every successful run:

`news.xml`  
The aggregated RSS feed. This is the canonical syndication output.

`news-index.json`  
A compact JSON manifest used by clients to discover numbered entry files without downloading all entries at once.

`news/{n}.json`  
One JSON file per entry (`news/1.json`, `news/2.json`, ...), ordered newest-first.

No additional publish step runs after these files are written. A `planet.py`
or `rss-aggregator` run finishes once the built-in outputs have been generated.

For a tiny static client example that reads `news-index.json` and renders numbered entries, see [frontend/minimal](../frontend/minimal/README.md).

### Numbered JSON schema

`news-index.json` has this shape:

```json
{
  "total": 2,
  "urls": ["news/1.json", "news/2.json"]
}
```

Each numbered entry keeps the normalized per-item data:

```json
{
  "id": "tag:example.com,2026:1",
  "url": "https://example.com/article",
  "title": "Example title",
  "summary": "Plain-text summary",
  "content": "Optional plain-text content",
  "image": {
    "url": "https://example.com/image.jpg",
    "mime_type": "image/jpeg",
    "data_base64": "..."
  },
  "source": "https://feed.example.org/rss.xml",
  "author": "Author name",
  "date": "2026-04-24T03:06:51Z",
  "tags": ["security"]
}
```

Fields are omitted when unavailable. `summary` and `content` are plain text in the JSON output.

### Image embedding and cache behavior

For each entry image URL, Venus first downloads to cache, validates the payload as an image, and then decides embedding:

- If validated size is `<= 1 MiB`, numbered JSON includes inline `image.data_base64` and `image.mime_type`.
- If validated size is `> 1 MiB`, numbered JSON keeps URL-only image metadata.
- If download or validation fails, numbered JSON keeps URL-only image metadata.

Image cache files are kept under `output_dir/images/`.

### Renumbering behavior

Numbered files are always rewritten newest-first. When fresher entries arrive, existing entry numbers shift (`news/1.json` becomes older items at `news/2.json`, etc.), and stale numeric files are removed.

### No theme selection

Older Venus releases could render multiple themed outputs through template engines. The maintained output model is now fixed: one RSS file (`news.xml`) plus indexed numbered JSON files. Output customization happens by changing normalized feed data through the built-in filtering options, not by choosing a theme.
