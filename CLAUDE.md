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
- `gutenbit/db.py` — SQLite storage

## Style

- Modern Python (3.11+), type-annotated
- Keep it simple — stdlib where possible, minimal dependencies
- No unnecessary abstractions
