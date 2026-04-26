## Minimal Frontend Example

This directory contains a single-file static frontend that reads Venus JSON output and renders clickable news pills.

It is intentionally small and heavily commented so it can be used as a base template for production frontends.

### Configuration

Edit these constants in [index.html](index.html):

- `NEWS_BASE_URL`: URL of the directory that contains `news-index.json` and `news/`.
- `ITEMS_TO_SHOW`: number of newest items to request and render.
- `SHOW_DATE`: `true` to render each entry date (when present).
- `SHOW_SOURCE`: `true` to render each entry source (when present).

### Local Run

Use a static server. Opening `index.html` directly from disk may fail because browsers restrict `fetch()` from `file://` pages.

```bash
python3 -m http.server 8000
```

Then open:

`http://127.0.0.1:8000/frontend/minimal/index.html`

Example directory layout expected by `NEWS_BASE_URL`:

```text
output/
  news-index.json
  news/
    1.json
    2.json
```
