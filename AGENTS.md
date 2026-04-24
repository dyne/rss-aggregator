# Repository Guidelines

## Project Structure & Module Organization

Venus is a Python feed aggregator. Top-level scripts such as `planet.py`,
`spider.py`, `publish.py`, and `expunge.py` are command entry points. Core
implementation lives in `planet/`, with shell adapters in `planet/shell/` and
the remaining legacy htmltmpl adapter in `planet/vendor/`. Tests are in
`tests/`, with fixtures under `tests/data/`. User-facing documentation is
straight XHTML in `docs/`. Feed filters live in `filters/`, themes in
`themes/`, and sample configurations in `examples/`.

## Build, Test, and Development Commands

- `uv sync`: install locked Python 3 runtime dependencies from `uv.lock`.
- `uv run python runtests.py`: run the full unittest suite.
- `uv run python runtests.py -v`: run tests with debug logging and verbose
  output.
- `uv run python runtests.py test_scrub.py`: run one test module from `tests/`.
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

Tests use the standard library `unittest` framework through `runtests.py`.
Add regression tests beside related coverage in `tests/`, and put reusable
fixtures in `tests/data/`. Name new test modules `test_<feature>.py` so the
runner discovers them automatically. For code changes, run the touched test
module first, then `uv run python runtests.py` before handing off.

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
