# Repository Guidelines

## Project Structure & Module Organization

Venus is a Python feed aggregator. `planet.py` is the only supported command
entry point. Core implementation lives in `src/`, with a minimal helper
module in `src/shell/` used only by the maintained built-in filter paths.
Built-in output generation lives in `src/output.py` and always writes
`rss.xml` plus `feed.json`. Tests are in `tests/`, with fixtures under
`tests/data/`. User-facing documentation is Markdown in `docs/`, maintained
filter helpers live in `filters/`, and sample configurations live in
`examples/`.

## Build, Test, and Development Commands

- `uv sync`: install locked Python 3 runtime dependencies from `uv.lock`.
- `uv run pytest`: run the full maintained test suite.
- `uv run pytest tests/test_scrub.py`: run one test module from `tests/`.
- `uv run pytest --cov=src --cov-report=term-missing --cov-report=xml`:
  generate local coverage reports.
- `uv build`: build the sdist and wheel.
- `uvx --from ./dist/rss_aggregator-3.0.0-py3-none-any.whl rss-aggregator --help`:
  smoke-test the packaged console script.
- `uv run python planet.py pathto/config.ini`: run the aggregator with a local
  configuration.

There is no generated build step. Work directly from the checkout and keep
commands runnable from the repository root.

## Coding Style & Naming Conventions

Keep changes small and readable. The codebase targets Python 3 while retaining
some legacy structure, so do not modernize unrelated files while making a
focused change. Follow the surrounding style: four-space indentation, simple
module-level functions, lowercase module names, and `test_*.py` test files.
Use native docstrings for new functions when behavior is not obvious. Prefer
well-known algorithms and plain control flow over new abstractions.

## Testing Guidelines

Tests are run with `pytest`, while most existing test modules still use the
standard library `unittest` style under pytest collection. Add regression tests
beside related coverage in `tests/`, and put reusable fixtures in `tests/data/`.
Name new test modules `test_<feature>.py` so pytest discovers them
automatically. For code changes, run the touched test module first, then
`uv run pytest` before handing off. When coverage matters, use
`uv run pytest --cov=src --cov-report=term-missing --cov-report=xml`.
For incremental coverage work, start with deterministic modules such as
`src/storage.py`, `src/output.py`, `src/media.py`, `src/expunge.py`,
and `src/config.py` before broader stateful paths like `src/spider.py`.

## Commit & Pull Request Guidelines

Recent history uses short imperative commit subjects, for example
`Handle varieties of empty <georss:point> element`. Keep commits scoped to one
behavioral change. Pull requests should describe the problem, summarize the
change, mention affected commands or configuration files, and include test
results. Include documentation updates under `docs/` when user-visible
behavior or configuration changes.

## Agent-Specific Instructions

Never over-engineer. Challenge first ideas, weigh simpler alternatives, and
choose the minimal viable implementation. Do not add dependencies unless asked;
suggest them only when they clearly simplify the work. When planning, write
Org files in `.gestalt/plans/` and do not commit `.gestalt` files.

## Dependency Policy

Prefer the Python standard library for small IO, HTTP, locking, and process
wrappers. Use maintained PyPI packages for parser or security-sensitive code
such as feed and HTML parsing. Do not vendor dependencies unless upstream is
unavailable and the code is small enough to audit locally; document the reason
in `pyproject.toml` or `docs/`.

## Maintained Product Shape

Keep the product surface narrow: Venus aggregates feeds and emits built-in
`rss.xml` and `feed.json` outputs. Template backends and themed output files
are no longer part of the maintained runtime. Media enrichment is limited to
feed-declared images plus bounded source-page Open Graph lookups cached through
the normal feed metadata path.

The maintained filter contract is also narrow: use built-in `excerpt`,
`regexp`, and `sed` config options instead of generic `filters = ...`,
`filter_directories`, or per-filter config sections. `sed` accepts only the
bundled short names in `filters/stripAd/`.

## Security Boundaries

Treat feed and feed-metadata URLs as untrusted input. Open Graph enrichment
must stay limited to public `http`/`https` targets and must not fetch
`file://` or private/loopback/link-local network destinations. Keep response
body limits in place for remote fetches (`src/net.py`) to avoid memory and
parser amplification. Preserve sanitizer and RSS/JSON output invariants:
active HTML payloads must remain neutralized, and RSS CDATA sections must
escape embedded `]]>` sequences.
