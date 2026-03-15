"""Shared CLI utility functions, constants, types, and formatting helpers."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, TypedDict

import click

from gutenbit.catalog import Catalog, CatalogFetchInfo
from gutenbit.db import ChunkRecord, Database
from gutenbit.display import CliDisplay

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR_NAME = ".gutenbit"
DEFAULT_DB_NAME = "gutenbit.db"
DEFAULT_DB = f"~/{STATE_DIR_NAME}/{DEFAULT_DB_NAME}"
DEFAULT_DOWNLOAD_DELAY = 2.0
DEFAULT_TOC_EXPAND = "2"
JSON_OPENING_LINE_PREVIEW_CHARS = 140
DEFAULT_OPENING_CHUNK_COUNT = 3
DEFAULT_VIEW_FORWARD = 1
JSON_BOOK_ID_KEY = "book_id"
OPENING_PREVIEW_PARAGRAPH_LIMIT = 4
OPENING_SECTION_SKIP_HEADINGS = frozenset(
    {
        "preface",
        "introduction",
        "foreword",
        "prologue",
        "contents",
        "table of contents",
        "list of illustrations",
        "illustrations",
        "transcriber's note",
        "transcribers note",
        "author's note",
        "authors note",
    }
)
_TITLE_STYLE_CONNECTORS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)
_TITLE_STYLE_WORD_RE = re.compile(r"^[A-Za-z]+(?:['\u2019][A-Za-z]+)*$")
_ROMAN_NUMERAL_RE = re.compile(r"^[IVXLCDM]+$", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r'[.!?]["\')\]]*$')

# ---------------------------------------------------------------------------
# Click infrastructure
# ---------------------------------------------------------------------------

_CONTEXT_SETTINGS: dict[str, Any] = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 100,
}

_DB_HELP = "SQLite database path (default: ~/.gutenbit/gutenbit.db)"
_DB_OVERRIDE_HELP = "SQLite database path (works before or after the subcommand)"
_VERBOSE_HELP = "enable debug logging"

# ---------------------------------------------------------------------------
# Display cache and logging
# ---------------------------------------------------------------------------

_DISPLAY_CACHE: tuple[int, int, CliDisplay] | None = None


def _configure_logging(verbose: bool) -> None:
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s %(name)s: %(message)s",
            stream=sys.stdout,
        )
    else:
        logging.basicConfig(level=logging.WARNING, format="%(message)s", stream=sys.stdout)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _display() -> CliDisplay:
    global _DISPLAY_CACHE
    stdout = sys.stdout
    stderr = sys.stderr
    cache_key = (id(stdout), id(stderr))
    if _DISPLAY_CACHE is None or _DISPLAY_CACHE[:2] != cache_key:
        _DISPLAY_CACHE = (*cache_key, CliDisplay(stdout=stdout, stderr=stderr))
    return _DISPLAY_CACHE[2]


# ---------------------------------------------------------------------------
# Path management
# ---------------------------------------------------------------------------


def _cli_state_dir() -> Path:
    return Path.home() / STATE_DIR_NAME


def _resolved_cli_path(path: str | Path) -> Path:
    """Resolve a CLI path the same way Database() will interpret it."""
    return Path(path).expanduser().resolve()


def _collapse_home_path(path: Path) -> str:
    """Render paths under the home directory with a leading tilde."""
    home = Path.home()
    try:
        relative = path.relative_to(home)
    except ValueError:
        return str(path)
    return str(Path("~") / relative) if relative.parts else "~"


def _display_cli_path(path: str | Path) -> str:
    """Render a user-facing path without turning ``~/...`` into ``<cwd>/~/...``."""
    raw = str(path)
    if raw.startswith("~"):
        return _collapse_home_path(_resolved_cli_path(path))
    return raw


def _catalog_cache_dir() -> Path:
    return _cli_state_dir() / "cache"


def _catalog_status_message(fetch_info: CatalogFetchInfo | None, *, refresh: bool) -> str:
    corpus = "English text corpus"
    if fetch_info is None:
        return f"Loading catalog ({corpus})."
    if fetch_info.source == "cache":
        return f"Using cached catalog ({corpus})."
    if fetch_info.source == "stale_cache":
        return f"Catalog download failed; using stale cached catalog ({corpus})."
    if refresh:
        return f"Refreshed catalog from Project Gutenberg ({corpus})."
    return f"Downloaded catalog from Project Gutenberg ({corpus})."


# ---------------------------------------------------------------------------
# Catalog and text normalization
# ---------------------------------------------------------------------------


def _load_catalog(refresh: bool = False, *, display: CliDisplay, as_json: bool) -> Catalog:
    catalog = Catalog.fetch(
        cache_dir=_catalog_cache_dir(),
        refresh=refresh,
    )
    if not as_json:
        display.status(
            _catalog_status_message(
                catalog.fetch_info,
                refresh=refresh,
            )
        )
    return catalog


def _normalize_apostrophes(s: str) -> str:
    """Replace curly/typographic apostrophes with ASCII for matching."""
    return s.replace("\u2019", "'").replace("\u2018", "'")


# ---------------------------------------------------------------------------
# TypedDict definitions
# ---------------------------------------------------------------------------


class _SectionState(TypedDict):
    heading: str
    path: str
    position: int
    paragraphs: int
    chars: int
    first_position: int
    opening_candidates: list[str]


class _BookSummary(TypedDict):
    id: int
    title: str
    authors: str
    language: str
    issued: str
    type: str
    locc: str
    subjects: list[str]
    bookshelves: list[str]


class _ChunkCounts(TypedDict):
    heading: int
    text: int


class _OverviewSummary(TypedDict):
    chunks_total: int
    chunk_counts: _ChunkCounts
    sections_total: int
    sections_shown: int
    levels_total: int
    levels_shown: int
    paragraphs_total: int
    chars_total: int
    est_words: int
    est_read_time: str


class _SectionRow(TypedDict):
    section_number: int
    section: str
    position: int
    paras: int
    chars: int
    est_words: int
    est_read: str
    opening_line: str


class _QuickActions(TypedDict):
    toc_expand_all: str
    search: str
    view_first_section: str
    view_by_position: str
    view_all: str


class _SectionSummary(TypedDict):
    book: _BookSummary
    overview: _OverviewSummary
    sections: list[_SectionRow]
    quick_actions: _QuickActions


# ---------------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------------


def _json_envelope(
    command: str,
    *,
    ok: bool,
    data: dict[str, Any] | list[Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "command": command,
        "data": data,
        "warnings": warnings or [],
        "errors": errors or [],
    }


def _print_json_envelope(
    command: str,
    *,
    ok: bool,
    data: dict[str, Any] | list[Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> None:
    print(
        json.dumps(
            _json_envelope(command, ok=ok, data=data, warnings=warnings, errors=errors),
            indent=2,
        )
    )


def _command_error(
    command: str,
    message: str,
    *,
    as_json: bool,
    display_message: str | None = None,
    code: int = 1,
    data: dict[str, Any] | list[Any] | None = None,
    warnings: list[str] | None = None,
) -> int:
    if as_json:
        _print_json_envelope(command, ok=False, data=data, warnings=warnings, errors=[message])
    else:
        _display().error(display_message or message)
    return code


# ---------------------------------------------------------------------------
# Text utility functions
# ---------------------------------------------------------------------------


def _no_chunks_message(db: Database, book_id: int) -> str:
    """Return a descriptive error for a book with no chunks."""
    if db.book(book_id) is None:
        return f"Book {book_id} is not in the database. Use 'gutenbit add {book_id}' to add it."
    return f"No chunks found for book {book_id}."


def _book_id_ref(book_id: int, *, capitalize: bool = True) -> str:
    prefix = "Book ID" if capitalize else "book ID"
    return f"{prefix} {book_id}"


def _no_chunks_display_message(db: Database, book_id: int) -> str:
    """Return the human-facing no-chunks message with an explicit book ID label."""
    if db.book(book_id) is None:
        return (
            f"{_book_id_ref(book_id)} is not in the database. "
            f"Use 'gutenbit add {book_id}' to add it."
        )
    return f"No chunks found for {_book_id_ref(book_id, capitalize=False)}."


def _preview(text: str, limit: int) -> str:
    flat = text.replace("\n", " ")
    if len(flat) <= limit:
        return flat
    return flat[:limit] + "…"


def _single_line(text: str) -> str:
    """Collapse all whitespace so tabular CLI output stays on one line."""
    return " ".join(text.split())


def _opening_preview_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in text.split():
        token = raw.strip("()[]{}\"'""'',;:-")
        if not token:
            continue
        tokens.append(token)
    return tokens


def _is_title_style_token(token: str) -> bool:
    if _ROMAN_NUMERAL_RE.fullmatch(token):
        return True
    if token.isupper() and any(ch.isalpha() for ch in token):
        return True
    if not _TITLE_STYLE_WORD_RE.fullmatch(token):
        return False
    lower = token.casefold()
    if lower in _TITLE_STYLE_CONNECTORS:
        return True
    return token[0].isupper() and token[1:] == token[1:].lower()


def _looks_like_opening_title_line(text: str) -> bool:
    flat = _single_line(text).strip()
    if not flat or _SENTENCE_END_RE.search(flat):
        return False
    if "," in flat or ";" in flat:
        return False
    tokens = _opening_preview_tokens(flat)
    if not tokens or len(tokens) > 8:
        return False
    return all(_is_title_style_token(token) for token in tokens)


def _select_section_opening_line(paragraphs: list[str]) -> str:
    """Choose a representative opening line for a section preview.

    Keep the first paragraph as the fallback, but skip a short title-like
    opening block when it is immediately followed by body text.
    """
    preview_lines: list[str] = []
    for text in paragraphs:
        flat = _single_line(text)
        if flat:
            preview_lines.append(flat)
    if not preview_lines:
        return ""

    prefix_len = 0
    while prefix_len < len(preview_lines) and _looks_like_opening_title_line(
        preview_lines[prefix_len]
    ):
        prefix_len += 1

    if prefix_len < len(preview_lines):
        first_line = preview_lines[0]
        if prefix_len > 1 or first_line.endswith(":"):
            return preview_lines[prefix_len]

    return preview_lines[0]


# ---------------------------------------------------------------------------
# FTS query utilities
# ---------------------------------------------------------------------------


def _fts_phrase_query(query: str) -> str:
    """Wrap a raw query as an exact FTS5 phrase, escaping inner quotes."""
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


# FTS5 operator tokens that signal an intentional advanced query.
_FTS_OPERATOR_RE = re.compile(
    r"""
    \bAND\b | \bOR\b | \bNOT\b | \bNEAR\b
    | [*"()\^]
    """,
    re.VERBOSE,
)
_SEARCH_QUERY_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)*")
_SEARCH_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "before",
        "being",
        "call",
        "could",
        "first",
        "from",
        "have",
        "having",
        "however",
        "into",
        "little",
        "never",
        "ought",
        "shall",
        "should",
        "since",
        "some",
        "there",
        "these",
        "those",
        "through",
        "under",
        "until",
        "upon",
        "when",
        "where",
        "which",
        "while",
        "would",
        "years",
    }
)


def _has_fts_operators(query: str) -> bool:
    """Return True if *query* contains FTS5 operator syntax."""
    return bool(_FTS_OPERATOR_RE.search(query))


def _safe_fts_query(query: str) -> str:
    """Escape a plain-text query so punctuation doesn't trigger FTS5 errors.

    Each whitespace-separated token is individually quoted so that
    apostrophes, hyphens, periods, and other punctuation are treated as
    literal characters while FTS5 still performs an implicit-AND across
    tokens.
    """
    tokens = query.split()
    if not tokens:
        return query
    quoted = [_fts_phrase_query(t) for t in tokens]
    return " ".join(quoted)


def _quick_action_search_query(rows: list[ChunkRecord]) -> str:
    """Choose a real in-book token for quick-action search examples."""
    text_rows = [row.content for row in rows if row.kind == "text"]
    for content in text_rows:
        tokens = _SEARCH_QUERY_TOKEN_RE.findall(content)
        for token in tokens:
            if len(token) >= 4 and token.casefold() not in _SEARCH_QUERY_STOPWORDS:
                return token
    for content in text_rows:
        tokens = _SEARCH_QUERY_TOKEN_RE.findall(content)
        if tokens:
            return tokens[0]
    return "chapter"


# ---------------------------------------------------------------------------
# Formatting and display helpers
# ---------------------------------------------------------------------------


def _format_int(value: int) -> str:
    return f"{value:,}"


def _json_search_filters(
    *,
    author: str | None,
    title: str | None,
    book_id: int | None,
    kind: str,
    section: str | None,
) -> dict[str, Any]:
    return {
        "author": author,
        "title": title,
        JSON_BOOK_ID_KEY: book_id,
        "kind": kind,
        "section": section,
    }


def _section_path(*levels: str) -> str:
    return " / ".join(level for level in levels if level) or "(unsectioned opening)"


def _section_path_parts(section: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in section.split(" / ") if part.strip())


def _section_depth(section: str) -> int:
    return len(_section_path_parts(section)) or 1


def _split_semicolon_list(raw: str) -> list[str]:
    return [_single_line(part) for part in raw.split(";") if part.strip()]


def _summarize_semicolon_list(raw: str, *, max_items: int) -> str:
    items = _split_semicolon_list(raw)
    if not items:
        return ""
    if len(items) <= max_items:
        return "; ".join(items)
    shown = "; ".join(items[:max_items])
    return f"{shown}; +{len(items) - max_items} more"


def _estimate_read_time(words: int, *, wpm: int = 250) -> str:
    if words <= 0:
        return "n/a"
    minutes = max(1, round(words / wpm))
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def _book_payload(book: Any) -> dict[str, Any]:
    return {
        "id": book.id,
        "title": _single_line(book.title),
        "authors": _single_line(book.authors),
        "language": _single_line(book.language),
        "subjects": _single_line(book.subjects),
        "locc": _single_line(book.locc),
        "bookshelves": _single_line(book.bookshelves),
        "issued": _single_line(book.issued),
        "type": _single_line(book.type),
    }


def _joined_chunk_text(
    rows: list[ChunkRecord],
) -> str:
    return "\n\n".join(row.content for row in rows)


def _indent_block(text: str, prefix: str = "    ") -> str:
    lines = text.splitlines()
    if not lines:
        return prefix if text else ""
    return "\n".join(f"{prefix}{line}" if line else "" for line in lines)


def _passage_payload(
    *,
    book_id: int,
    title: str,
    author: str,
    section: str | None,
    section_number: int | None,
    position: int | None,
    forward: int | None,
    radius: int | None,
    all_scope: bool | None = None,
    content: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        JSON_BOOK_ID_KEY: book_id,
        "title": title,
        "author": author,
        "section": section,
        "section_number": section_number,
        "position": position,
        "forward": forward,
        "radius": radius,
        "all": all_scope,
        "content": content,
    }
    if extras:
        payload.update(extras)
    return payload


def _passage_header(payload: dict[str, Any]) -> str:
    parts = [
        f"{JSON_BOOK_ID_KEY}={payload[JSON_BOOK_ID_KEY]}",
        f"title={payload['title']}",
    ]
    if payload.get("author"):
        parts.append(f"author={payload['author']}")
    if payload.get("section"):
        parts.append(f"section={payload['section']}")
    if payload.get("section_number") is not None:
        parts.append(f"section_number={payload['section_number']}")
    if payload.get("position") is not None:
        parts.append(f"position={payload['position']}")
    if payload.get("forward") is not None:
        parts.append(f"forward={payload['forward']}")
    if payload.get("radius") is not None:
        parts.append(f"radius={payload['radius']}")
    if payload.get("all"):
        parts.append("all")
    return "  ".join(parts)


def _print_key_value_table(
    rows: list[tuple[str, str]],
    *,
    show_header: bool = True,
    key_header: str = "Field",
    value_header: str = "Value",
) -> None:
    if not rows:
        return
    key_width = max(len(key_header), max(len(key) for key, _ in rows))
    if show_header:
        print(f"  {key_header:<{key_width}}  {value_header}")
        print(f"  {'-' * key_width}  {'-' * len(value_header)}")
    for key, value in rows:
        shown = _single_line(value) if value else "-"
        print(f"  {key:<{key_width}}  {shown}")


def _print_table(headers: list[str], rows: list[list[str]], *, right_align: set[int]) -> None:
    if not headers:
        return
    widths = []
    for idx, header in enumerate(headers):
        widest = len(header)
        for row in rows:
            widest = max(widest, len(row[idx]))
        widths.append(widest)

    def _fmt(cell: str, idx: int) -> str:
        width = widths[idx]
        if idx in right_align:
            return f"{cell:>{width}}"
        return f"{cell:<{width}}"

    print("  " + "  ".join(_fmt(header, i) for i, header in enumerate(headers)))
    print("  " + "  ".join("-" * width for width in widths))
    for row in rows:
        print("  " + "  ".join(_fmt(cell, i) for i, cell in enumerate(row)))


def _print_block_header(title: str) -> None:
    print(f"\n[{title.upper()}]")


# ---------------------------------------------------------------------------
# CLI context resolvers
# ---------------------------------------------------------------------------


def _resolve_db(ctx: click.Context, db: str | None) -> str:
    """Return effective db path: subcommand override takes precedence over group default."""
    if db is not None:
        return db
    return ctx.obj.get("db", DEFAULT_DB)


def _resolve_verbose(ctx: click.Context, verbose: bool) -> bool:
    """Return effective verbose flag: either source activates it."""
    return verbose or ctx.obj.get("verbose", False)


# ---------------------------------------------------------------------------
# Miscellaneous helpers
# ---------------------------------------------------------------------------


def _format_fts_error(exc: sqlite3.Error) -> str:
    detail = " ".join(str(exc).split()).strip().rstrip(".")
    if not detail:
        return "Invalid FTS query syntax."
    return f"Invalid FTS query syntax: {detail}."


def _toc_expand_depth(expand: str) -> int:
    return 4 if expand == "all" else int(expand)
