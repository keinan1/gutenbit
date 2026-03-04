# gutenbit

ETL package for Project Gutenberg: download, parse, and store texts in SQLite.

## Commands

- `uv run pytest` — Run tests
- `uv run ruff check .` — Lint
- `uv run ruff format --check .` — Check formatting
- `uv run ty check` — Type check

## Architecture

- `gutenbit/catalog.py` — CSV catalog fetch and search
- `gutenbit/download.py` — Text download and header/footer stripping
- `gutenbit/chunker.py` — Structural text chunking
- `gutenbit/db.py` — SQLite storage with FTS5 search

### Chunker

Splits book text into labelled chunks. Kinds: `front_matter` (title page, etc.),
`toc` (table of contents), `heading` (chapter/section headings), `paragraph` (prose),
`end_matter` (footnotes, appendices, etc.).

## Style

- Modern Python (3.11+), type-annotated
- Keep it simple — stdlib where possible, minimal dependencies
