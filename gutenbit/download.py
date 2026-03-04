"""Download and clean Project Gutenberg texts."""

from __future__ import annotations

import httpx

TEXT_URL = "https://www.gutenberg.org/ebooks/{id}.txt.utf-8"


def download_text(book_id: int) -> str:
    """Download raw text for a book from Project Gutenberg."""
    url = TEXT_URL.format(id=book_id)
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return response.text


def _is_marker_line(line: str) -> bool:
    """Check if a line is a Project Gutenberg START/END delimiter."""
    stripped = line.strip().upper()
    return stripped.startswith("***") and "PROJECT GUTENBERG" in stripped


def strip_headers(text: str) -> str:
    """Remove Project Gutenberg headers and footers, returning only the book content."""
    lines = text.splitlines()
    start: int | None = None
    end = len(lines)

    for i, line in enumerate(lines):
        if _is_marker_line(line):
            if start is None:
                start = i + 1
            else:
                end = i
                break

    if start is None:
        return text.strip()

    return "\n".join(lines[start:end]).strip()
