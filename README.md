# gutenbit

Download, parse, and store [Project Gutenberg](https://www.gutenberg.org/) texts in SQLite.

## Install

```bash
uv sync
```

## Usage

```python
from gutenbit import Catalog, Database

# Fetch the catalog and search for books
catalog = Catalog.fetch()
books = catalog.search(author="Shakespeare", language="en")

# Download texts and store them in SQLite
with Database("gutenberg.db") as db:
    db.ingest(books)

    # Retrieve cleaned text
    text = db.text(book_id=1661)

    # Full-text search with BM25 ranking
    results = db.search("to be or not to be")

    # Filter by metadata
    results = db.search("whale", author="melville", language="en")

    for r in results:
        print(f"[{r.title}] {r.chapter} (score={r.score:.1f})")
        print(r.content[:200])
```

Texts are automatically chunked into paragraphs during ingest, with chapter headings detected and tracked. Each search result includes the matching paragraph, its chapter, position, book metadata, and a BM25 relevance score.

## Development

```bash
uv run pytest                    # tests
uv run ruff check .              # lint
uv run ruff format --check .     # format check
uv run ty check                  # type check
```

## License

MIT
