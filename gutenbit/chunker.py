"""Split book text into labelled chunks with chapter detection.

Every text block separated by blank lines is preserved and labelled with a
*kind* so that downstream consumers can reconstruct the full original text
or filter to just the content they need.

Chunk kinds
-----------
- ``"paragraph"`` — one or more consecutive prose blocks accumulated to a
  minimum length (≥ 50 chars).  Short blocks like dialogue lines are merged
  with their neighbours rather than standing alone.
- ``"heading"``   — chapter / section headings
- ``"separator"`` — decorative rules and dinkuses (``* * *``, ``---``, …)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Matches common chapter/part/book headings.
# Examples: "CHAPTER I", "Chapter 12", "BOOK III", "Part 2", "ACT IV", "SCENE 2"
_HEADING_RE = re.compile(
    r"^(?:CHAPTER|BOOK|PART|ACT|SCENE|SECTION)"
    r"\s+[\dIVXLCDMivxlcdm]+\.?(?:\s.*)?$",
    re.IGNORECASE,
)

# Matches decorative separators / dinkuses.
# Covers patterns like: * * *, ***, ---, ===, ~~~, _ _ _, -----, etc.
_SEPARATOR_RE = re.compile(
    r"^[\s*\-=_~.#·•]+$",
)

# Minimum character length for a paragraph chunk.  Consecutive text blocks
# are accumulated until this threshold is met (or a structural break occurs).
_MIN_CHUNK_LEN = 50


@dataclass(frozen=True, slots=True)
class Chunk:
    """A discrete text block extracted from a book, labelled by kind."""

    position: int
    chapter: str
    content: str
    kind: str  # "paragraph", "heading", or "separator"


def chunk_text(text: str) -> list[Chunk]:
    """Split *text* into labelled chunks, tracking chapter headings.

    Text blocks (separated by blank lines) are accumulated into paragraph
    chunks until they reach ``_MIN_CHUNK_LEN`` characters.  Headings and
    separators are emitted as their own chunks and act as flush points —
    any buffered text is emitted first, even if below minimum length.

    This means **no text is discarded**.  Short dialogue lines, brief
    narration, and other small blocks are grouped with their neighbours
    into paragraph chunks.  Trailing text before a section break (or at
    end-of-document) is emitted as its own chunk even if below minimum.

    Returns chunks in document order so that
    ``"\\n\\n".join(c.content for c in chunks)`` reproduces the text.
    """
    blocks = re.split(r"\n\s*\n", text)
    chunks: list[Chunk] = []
    chapter = ""
    position = 0
    buffer: list[str] = []

    def _flush() -> None:
        nonlocal position
        if not buffer:
            return
        content = "\n\n".join(buffer)
        chunks.append(Chunk(position=position, chapter=chapter, content=content, kind="paragraph"))
        position += 1
        buffer.clear()

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if _is_heading(block):
            _flush()
            chapter = _normalise_heading(block)
            chunks.append(Chunk(position=position, chapter=chapter, content=block, kind="heading"))
            position += 1
        elif _is_separator(block):
            _flush()
            chunks.append(
                Chunk(position=position, chapter=chapter, content=block, kind="separator")
            )
            position += 1
        else:
            buffer.append(block)
            if sum(len(b) for b in buffer) >= _MIN_CHUNK_LEN:
                _flush()

    _flush()  # emit any remaining buffered text
    return chunks


def _is_heading(block: str) -> bool:
    """Return True if *block* looks like a chapter/section heading."""
    lines = block.splitlines()
    if len(lines) > 3:
        return False
    first = lines[0].strip()
    return bool(_HEADING_RE.match(first))


def _is_separator(block: str) -> bool:
    """Return True if *block* is a decorative rule or dinkus."""
    # Must be a single line and match the separator pattern.
    if "\n" in block:
        return False
    return bool(_SEPARATOR_RE.fullmatch(block))


def _normalise_heading(block: str) -> str:
    """Clean up a heading block into a concise chapter label."""
    return " ".join(block.split())
