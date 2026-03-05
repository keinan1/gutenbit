"""Command-line interface for gutenbit."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from gutenbit.catalog import Catalog
from gutenbit.db import Database

DEFAULT_DB = "gutenbit.db"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gutenbit", description="Project Gutenberg ETL tool")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite database path (default: %(default)s)")
    p.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    sub = p.add_subparsers(dest="command")

    # --- catalog ---
    cat = sub.add_parser("catalog", help="search the Project Gutenberg catalog")
    cat.add_argument("--author", default="", help="filter by author")
    cat.add_argument("--title", default="", help="filter by title")
    cat.add_argument("--language", default="", help="filter by language")
    cat.add_argument("--subject", default="", help="filter by subject")
    cat.add_argument("-n", "--limit", type=int, default=20, help="max results (default: 20)")

    # --- ingest ---
    ing = sub.add_parser("ingest", help="download and store books by PG id")
    ing.add_argument("ids", nargs="+", type=int, help="Project Gutenberg book IDs")
    ing.add_argument("--delay", type=float, default=1.0, help="seconds between downloads")

    # --- books ---
    sub.add_parser("books", help="list books stored in the database")

    # --- chunks ---
    ch = sub.add_parser("chunks", help="show chunks for a stored book")
    ch.add_argument("book_id", type=int, help="Project Gutenberg book ID")
    ch.add_argument(
        "--kind",
        nargs="+",
        choices=["front_matter", "heading", "paragraph", "end_matter"],
        help="filter by chunk kind",
    )
    ch.add_argument("-n", "--limit", type=int, default=0, help="max chunks to show (0=all)")

    # --- search ---
    se = sub.add_parser("search", help="full-text search across stored books")
    se.add_argument("query", help="FTS5 search query")
    se.add_argument("--author", help="filter by author")
    se.add_argument("--title", help="filter by title")
    se.add_argument("--book-id", type=int, help="restrict to a single book")
    se.add_argument("--kind", help="filter by chunk kind")
    se.add_argument("-n", "--limit", type=int, default=20, help="max results (default: 20)")

    # --- text ---
    tx = sub.add_parser("text", help="print the full text of a stored book")
    tx.add_argument("book_id", type=int, help="Project Gutenberg book ID")

    return p


# -------------------------------------------------------------------
# Subcommand handlers
# -------------------------------------------------------------------


def _cmd_catalog(args: argparse.Namespace) -> int:
    print("Fetching catalog from Project Gutenberg…")
    catalog = Catalog.fetch()
    results = catalog.search(
        author=args.author,
        title=args.title,
        language=args.language,
        subject=args.subject,
    )
    if not results:
        print("No books found.")
        return 0
    shown = results[: args.limit]
    for b in shown:
        print(f"  {b.id:>6}  {b.authors[:30]:<30s}  {b.title}")
    if len(results) > args.limit:
        print(f"  … and {len(results) - args.limit} more (use -n to show more)")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    print("Fetching catalog…")
    catalog = Catalog.fetch()
    by_id = {b.id: b for b in catalog.records}
    books = []
    for book_id in args.ids:
        rec = by_id.get(book_id)
        if rec is None:
            print(f"  warning: book {book_id} not found in catalog, skipping")
            continue
        books.append(rec)

    if not books:
        print("No valid book IDs provided.")
        return 1

    with Database(args.db) as db:
        for book in books:
            print(f"  ingesting {book.id}: {book.title}…")
            db.ingest([book], delay=args.delay)
    print(f"Done. Database: {Path(args.db).resolve()}")
    return 0


def _cmd_books(args: argparse.Namespace) -> int:
    with Database(args.db) as db:
        books = db.books()
    if not books:
        print("No books stored yet. Use 'gutenbit ingest <id> ...' to add some.")
        return 0
    for b in books:
        print(f"  {b.id:>6}  {b.authors[:30]:<30s}  {b.title}")
    print(f"\n{len(books)} book(s) stored in {args.db}")
    return 0


def _cmd_chunks(args: argparse.Namespace) -> int:
    with Database(args.db) as db:
        rows = db.chunks(args.book_id, kinds=args.kind)
    if not rows:
        print(f"No chunks found for book {args.book_id}.")
        return 1
    limit = args.limit if args.limit > 0 else len(rows)
    for pos, div1, div2, div3, div4, content, kind, _char_count in rows[:limit]:
        divs = "/".join(d for d in [div1, div2, div3, div4] if d)
        tag = f"[{kind}]"
        preview = content[:120].replace("\n", " ")
        if len(content) > 120:
            preview += "…"
        print(f"  {pos:>5}  {tag:<14s}  {divs:<40s}  {preview}")
    total = len(rows)
    shown = min(limit, total)
    print(f"\n{shown}/{total} chunk(s) shown (book {args.book_id})")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    with Database(args.db) as db:
        results = db.search(
            args.query,
            author=args.author,
            title=args.title,
            book_id=args.book_id,
            kind=args.kind,
            limit=args.limit,
        )
    if not results:
        print("No results.")
        return 0
    for r in results:
        divs = "/".join(d for d in [r.div1, r.div2, r.div3, r.div4] if d)
        preview = r.content[:120].replace("\n", " ")
        if len(r.content) > 120:
            preview += "…"
        print(f"  [{r.book_id}] {r.title[:40]:<40s}  {divs}")
        print(f"         score={r.score:.2f}  kind={r.kind}  chars={r.char_count}")
        print(f"         {preview}")
        print()
    print(f"{len(results)} result(s)")
    return 0


def _cmd_text(args: argparse.Namespace) -> int:
    with Database(args.db) as db:
        content = db.text(args.book_id)
    if content is None:
        print(f"No text found for book {args.book_id}.")
        return 1
    print(content)
    return 0


_COMMANDS = {
    "catalog": _cmd_catalog,
    "ingest": _cmd_ingest,
    "books": _cmd_books,
    "chunks": _cmd_chunks,
    "search": _cmd_search,
    "text": _cmd_text,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.command:
        parser.print_help()
        return 0

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def _entry_point() -> None:
    """Console-scripts entry point."""
    sys.exit(main())
