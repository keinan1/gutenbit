# gutenbit

## Project overview

ETL package for Project Gutenberg: download, parse, and store texts in SQLite.

## Development setup

```bash
uv sync
```

## Commands

- `uv run pytest` — Run tests
- `uv run ruff check .` — Lint
- `uv run ruff format --check .` — Check formatting
- `uv run ty check` — Type check

## Architecture

- `gutenbit/catalog.py` — CSV catalog fetch and search
- `gutenbit/download.py` — Text download and header/footer stripping
- `gutenbit/chunker.py` — Text chunking with kind-labelled preservation of all blocks
- `gutenbit/db.py` — SQLite storage with FTS5 search

### Chunker design

Consecutive text blocks (separated by blank lines) are accumulated into paragraph
chunks until they reach a minimum length (50 chars). Headings and separators act
as flush points. Nothing is discarded — short dialogue, brief narration, etc. are
grouped with neighbouring blocks rather than standing alone.

Chunk kinds:

- `"paragraph"` — one or more consecutive prose blocks (accumulated to ≥ 50 chars)
- `"heading"` — chapter/section headings (also updates the running chapter label)
- `"separator"` — decorative rules, dinkuses (`* * *`, `---`, etc.)

Trailing text before a section break or end-of-document is emitted as its own chunk
even if below minimum. Users can reconstruct the full original text from all chunks
in position order, or filter to just `"paragraph"` for prose.

## Test corpus

Tests use excerpts from four Dickens novels (Project Gutenberg IDs):

- **The Pickwick Papers** — PG 580
- **Oliver Twist** — PG 730
- **The Old Curiosity Shop** — PG 700
- **Nicholas Nickleby** — PG 967

## Style

- Modern Python (3.11+), type-annotated
- Keep it simple — stdlib where possible, minimal dependencies
- No unnecessary abstractions
