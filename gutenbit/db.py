"""SQLite storage for Project Gutenberg books."""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from gutenbit.catalog import BookRecord
from gutenbit.download import download_text, strip_headers

logger = logging.getLogger(__name__)

SCHEMA = """\
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '',
    subjects TEXT NOT NULL DEFAULT '',
    locc TEXT NOT NULL DEFAULT '',
    bookshelves TEXT NOT NULL DEFAULT '',
    issued TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'Text'
);

CREATE TABLE IF NOT EXISTS texts (
    book_id INTEGER PRIMARY KEY REFERENCES books(id),
    content TEXT NOT NULL,
    downloaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Database:
    """SQLite database for storing Project Gutenberg books and their texts."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def ingest(self, books: list[BookRecord], *, delay: float = 1.0) -> None:
        """Download, clean, and store books. Skips books already in the database."""
        for book in books:
            if self._has_text(book.id):
                logger.info("Skipping %s (already downloaded)", book.title)
                continue

            logger.info("Downloading %s (id=%d)", book.title, book.id)
            try:
                raw = download_text(book.id)
                clean = strip_headers(raw)
                self._store(book, clean)
            except Exception:
                logger.exception("Failed to download %s (id=%d)", book.title, book.id)

            time.sleep(delay)

    def books(self) -> list[BookRecord]:
        """Return all stored books as BookRecords."""
        rows = self._conn.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [
            BookRecord(
                id=row["id"],
                title=row["title"],
                authors=row["authors"],
                language=row["language"],
                subjects=row["subjects"],
                locc=row["locc"],
                bookshelves=row["bookshelves"],
                issued=row["issued"],
                type=row["type"],
            )
            for row in rows
        ]

    def text(self, book_id: int) -> str | None:
        """Return the clean text for a book, or None if not found."""
        row = self._conn.execute(
            "SELECT content FROM texts WHERE book_id = ?", (book_id,)
        ).fetchone()
        return row["content"] if row else None

    def _has_text(self, book_id: int) -> bool:
        row = self._conn.execute("SELECT 1 FROM texts WHERE book_id = ?", (book_id,)).fetchone()
        return row is not None

    def _store(self, book: BookRecord, text: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO books"
                " (id, title, authors, language, subjects, locc, bookshelves, issued, type)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    book.id,
                    book.title,
                    book.authors,
                    book.language,
                    book.subjects,
                    book.locc,
                    book.bookshelves,
                    book.issued,
                    book.type,
                ),
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO texts (book_id, content) VALUES (?, ?)",
                (book.id, text),
            )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
