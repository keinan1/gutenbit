# Error Report: CLI Battle Test (Dickens Corpus, 16 Novels)

**Date:** 2026-03-07
**Branch:** `claude/test-cli-functionality-roCc8`
**Scope:** CLI functionality, HTML chunker output, end-to-end integrity

---

## Test Corpus

| # | Book | PG ID | Sections | Paras | Chars | Status |
|---|------|-------|----------|-------|-------|--------|
| 1 | A Christmas Carol | 46 | 5 | 712 | 156,377 | Clean |
| 2 | A Tale of Two Cities | 98 | 48 | 3,259 | 747,817 | Clean |
| 3 | The Mystery of Edwin Drood | 564 | 23 | 2,496 | 533,199 | Clean |
| 4 | The Pickwick Papers | 580 | 58 | 7,950 | 1,721,093 | Minor: CONTENTS leak |
| 5 | The Old Curiosity Shop | 700 | 73 | 4,021 | 1,200,250 | Minor: CONTENTS leak |
| 6 | Oliver Twist | 730 | 53 | 3,834 | 879,444 | Clean |
| 7 | David Copperfield | 766 | 67 | 7,114 | 1,914,154 | Minor: display issue |
| 8 | Hard Times | 786 | 41 | 2,308 | 568,010 | Minor: front matter noise |
| 9 | Dombey and Son | 821 | 64 | 7,247 | 1,973,321 | Clean |
| 10 | Our Mutual Friend | 883 | 71 | 8,412 | 1,788,623 | Clean |
| 11 | Barnaby Rudge | 917 | 79 | 4,614 | 1,406,592 | **BROKEN: 4 chapters missing** |
| 12 | Little Dorrit | 963 | 73 | 6,648 | 1,860,660 | Minor: CONTENTS leak |
| 13 | Nicholas Nickleby | 967 | 66 | 7,325 | 1,830,536 | Minor: CONTENTS leak |
| 14 | Martin Chuzzlewit | 968 | 56 | 7,160 | 1,862,706 | Minor: CONTENTS leak |
| 15 | Bleak House | 1023 | 68 | 7,170 | 1,921,288 | Clean |
| 16 | Great Expectations | 1400 | 59 | 3,833 | 984,695 | Clean |

### Commands Exercised

- Help: top-level + all 6 subcommands
- `catalog`: author/title/subject/language filters, combined filters, no-results, no-filters, JSON
- `ingest`: single/batch, re-ingest (skip), invalid IDs, JSON
- `books`: text + JSON, empty DB
- `view`: default summary, `--all`, `--position`, `--section`, `--around`, `--full`, `--kind`, `--json`
- `search`: ranked/first/last modes, `--phrase`, `--book-id`, `--author`, `--kind`, `--full`, `--json`
- `delete`: valid/invalid/already-deleted, JSON
- Edge cases: conflicting selectors, empty query, non-existent sections, out-of-range positions

---

## Critical Issues

### F-001: Barnaby Rudge (PG 917) — 4 chapters silently dropped

**Severity:** High
**Component:** `gutenbit/html_chunker.py:278`, `_find_next_heading()`
**Type:** Silent data loss

#### Symptom

Chapters 1, 6, 8, and 13 are completely absent from the chunked output.
Their paragraph content is absorbed into the preceding section:

- **Chapter 1** merged into PREFACE — PREFACE balloons to 118 paragraphs /
  39,978 chars (should be ~5 paragraphs about ravens)
- **Chapter 6** merged into Chapter 5
- **Chapter 8** merged into Chapter 7
- **Chapter 13** merged into Chapter 12

#### Root Cause

`_find_next_heading()` uses `find_all_next(limit=10)` when scanning from a
body anchor to locate its `<h2>` heading. In this illustrated edition, each
chapter boundary has 11 intervening elements between anchor and heading:

```html
<a id="link2HCH0001">           <!-- body anchor -->
  <div>                          <!-- 0 -->
  <br>                           <!-- 1 -->
  <br>                           <!-- 2 -->
  <br>                           <!-- 3 -->
  <br>                           <!-- 4 -->
  <div class="fig">              <!-- 5 (illustration wrapper) -->
  <img>                          <!-- 6 (illustration image) -->
  <br>                           <!-- 7 -->
  <h5> (illustration caption)   <!-- 8 -->
  <a>                            <!-- 9 -->
  <i>                            <!-- 10 — limit reached, search stops -->
  <h2>Chapter 1</h2>            <!-- 11 — MISSED -->
```

This pattern is identical for all four missing chapters. The `<h2>` heading
is exactly one element past the search limit.

#### Verification

```bash
uv run gutenbit --db test.db ingest 917 --delay 0
uv run gutenbit --db test.db view 917
# Observe: PREFACE → Chapter 2 (no Chapter 1)
#          Chapter 5 → Chapter 7 (no Chapter 6)
#          Chapter 7 → Chapter 9 (no Chapter 8)
#          Chapter 12 → Chapter 14 (no Chapter 13)
```

#### Impact

~15,000 words of novel text silently miscategorized. Users and agents cannot
navigate to these chapters by name. Search results for content in these
chapters show the wrong section metadata.

#### Recommended Fix

Increase the `limit` in `_find_next_heading()`. Options:

1. **Simple:** Raise limit from 10 to 25 (covers the 11-element pattern with margin)
2. **Robust:** Skip non-content elements (`<br>`, `<img>`, decorative `<div>`)
   when counting toward the limit, only counting structural tags
3. **Strongest:** Remove the limit entirely and scan until the next heading or
   end of document, with a maximum distance check based on document position
   rather than element count

---

### F-002: Pre-existing test failure — Sherlock Holmes 18 headings (expected 12)

**Severity:** Medium
**Component:** `gutenbit/html_chunker.py`, `_is_structural_toc_link()` / hierarchy
**Test:** `tests/test_battle.py:359`

#### Symptom

`TestSherlockHolmes.test_twelve_stories` expects 12 headings but gets 18.

#### Root Cause

The 6 extra headings are:

| # | Heading | Why it leaks through |
|---|---------|---------------------|
| 1 | `ADVENTURES OF SHERLOCK HOLMES` | Book title — treated as a section |
| 2 | `CONTENTS` | Front matter heading — not filtered |
| 3 | `ILLUSTRATIONS` | Front matter heading — not filtered |
| 4 | `I` | Roman numeral sub-section of "A Scandal in Bohemia" |
| 5 | `II` | Roman numeral sub-section of "A Scandal in Bohemia" |
| 6 | `III` | Roman numeral sub-section of "A Scandal in Bohemia" |

`_is_structural_toc_link()` only blocks citations, page numbers, footnotes,
and purely numeric text. It does not filter:
- Front-matter headings (CONTENTS, ILLUSTRATIONS)
- Book-level title headings
- Roman-numeral sub-sections within stories

#### Actual Chunker Output

```
ADVENTURES OF SHERLOCK HOLMES          ← spurious (title)
CONTENTS                               ← spurious (front matter)
ILLUSTRATIONS                          ← spurious (front matter)
ADVENTURES OF SHERLOCK HOLMES A SCANDAL IN BOHEMIA
I                                      ← spurious (sub-section)
II                                     ← spurious (sub-section)
III                                    ← spurious (sub-section)
THE RED-HEADED LEAGUE
A CASE OF IDENTITY
THE BOSCOMBE VALLEY MYSTERY
THE FIVE ORANGE PIPS
THE MAN WITH THE TWISTED LIP
THE ADVENTURE OF THE BLUE CARBUNCLE
THE ADVENTURE OF THE SPECKLED BAND
THE ADVENTURE OF THE ENGINEER'S THUMB
THE ADVENTURE OF THE NOBLE BACHELOR
THE ADVENTURE OF THE BERYL CORONET
THE ADVENTURE OF THE COPPER BEECHES
```

#### Recommended Fix

1. Filter TOC links whose heading text matches known non-content patterns
   (CONTENTS, ILLUSTRATIONS, TABLE OF CONTENTS)
2. Handle roman numeral sub-sections by classifying them as sub-divisions
   (div2) rather than top-level sections, or by detecting when a short
   heading (I, II, III, IV, etc.) follows a longer heading and treating
   it as a child

---

## Moderate Issues

### F-003: CONTENTS / front matter text leaking into paragraph chunks

**Severity:** Moderate
**Component:** `gutenbit/html_chunker.py:432`, `_is_toc_paragraph()`
**Affected:** PG 580, 700, 967, 968, 963

#### Symptom

The `(unsectioned opening)` section contains "CONTENTS" as its opening text.
In Pickwick Papers (580), this section has 3 paragraphs totaling 11,235 chars
of table-of-contents markup stored as regular paragraph chunks.

#### Root Cause

`_is_toc_paragraph()` only identifies a paragraph as TOC content if it
contains an `<a class="pginternal">` link. In these editions, CONTENTS
entries use plain text without pginternal links, so they pass through as
regular content paragraphs.

```python
def _is_toc_paragraph(paragraph: Tag) -> bool:
    if paragraph.find("a", class_="pginternal") is None:
        return False  # ← Plain-text TOC entries escape here
```

#### Impact

- Pollutes search results (searching for a chapter title may surface its
  TOC entry as a separate hit)
- Inflates character counts for the unsectioned opening section

#### Recommended Fix

Extend `_is_toc_paragraph()` to also detect:
- Paragraphs whose text is entirely or primarily a known heading name
  (matching section heading text exactly)
- Paragraphs consisting solely of a title + page number pattern
- Paragraphs within a container that has TOC-like structure (e.g., many
  short paragraphs with similar formatting before the first heading)

---

### F-004: Hard Times (PG 786) — 87 micro-paragraphs in front matter

**Severity:** Low-moderate
**Component:** `gutenbit/html_chunker.py`, front-matter boundary handling

#### Symptom

`(unsectioned opening)` contains 87 paragraphs with only 1,301 characters
total (~15 chars average). Opening text is "By CHARLES DICKENS".

#### Root Cause

The Gutenberg HTML has extensive front matter between the START delimiter and
the first section heading. Each line of the title block, CONTENTS listing,
and dedication is a separate `<p>` element. Since these lack `pginternal`
links, `_is_toc_paragraph()` does not filter them.

#### Impact

87 mostly-empty chunks in the database. Noise in search results, inflated
chunk counts. The 87:1301 ratio (avg 15 chars/chunk) is a strong signal
that these are not meaningful paragraphs.

#### Recommended Fix

Consider a minimum paragraph length threshold for front-matter content
(e.g., skip paragraphs < 20 chars before the first heading), or implement
a more aggressive front-matter detection heuristic.

---

## Display / Ergonomics Issues

### F-005: David Copperfield (PG 766) — unreadable section table

**Severity:** Low (display only)
**Component:** `gutenbit/cli.py:1029`, `_render_section_summary()`

#### Symptom

Every row in the CONTENTS table shows the same truncated prefix:
```
THE PERSONAL HISTORY AND EXPERIENCE O...
```

All 64 chapter sections are indistinguishable because div1 is the full
book title ("THE PERSONAL HISTORY AND EXPERIENCE OF DAVID COPPERFIELD
THE YOUNGER"), div2 holds the actual chapter name, and the 40-character
column width truncates before the chapter name is ever visible.

#### Root Cause

The section display joins div1/div2/div3/div4 with " / " and then
truncates to 40 characters. When div1 alone exceeds 40 characters, the
deeper levels (where the useful chapter names live) are never shown.

#### Recommended Fix

When truncation would completely hide the deepest level, prefer showing
the most specific level with an abbreviated prefix:
```
…/CHAPTER 1. — I AM BORN
…/CHAPTER 2. — I OBSERVE
```

Or increase the section column width dynamically when all sections share
a common prefix.

---

### F-006: `search --book-id` for non-existent book — no warning

**Severity:** Low
**Status:** **Fixed in this branch**

`gutenbit search "ghost" --book-id 99999` now prints
`warning: Book 99999 is not in the database.` and includes it in the JSON
`warnings` array. Previously returned "No results." with no indication the
book was missing.

---

## Outstanding Non-Chunker Issues

### F-007: Catalog fetch is uncached

**Severity:** Low-medium
**Component:** `gutenbit/catalog.py`

Every `catalog` and `ingest` command re-downloads and parses the full
Project Gutenberg catalog CSV (~1s latency). No local cache exists.

**Recommendation:** Add optional catalog cache with TTL and explicit
`--refresh` flag.

---

## Items Working Well

The following were thoroughly tested and found solid:

| Area | Verdict |
|------|---------|
| Help text (all 6 commands) | Clear, with useful examples and workflow guide |
| JSON envelope consistency | `{ok, command, data, warnings, errors}` across all commands |
| Error messages for bad sections | Shows available sections + tip command |
| Constraint enforcement | Conflicting selectors, invalid options all produce clear errors |
| Re-ingest behavior | Correctly skips current, reprocesses on chunker version change |
| Exit codes | 0 success, 1 error, 2 argparse, 130 interrupt |
| Delete safety | Proper warnings for missing books, correct exit codes |
| Search modes (ranked/first/last) | Correct orderings verified |
| View selectors (all/position/section) | Each works correctly with --around, --full, --kind |
| Phrase search | Correct FTS5 quoting and escaping |
| Multi-book operations | Batch ingest, cross-book search all work |

---

## Pre-existing Code Quality Notes

- **3 files had formatting drift** from `ruff format`: `gutenbit/db.py`,
  `gutenbit/html_chunker.py`, `tests/test_search.py`. **Fixed in this branch.**
- **Linting:** `ruff check .` passes clean.
- **Test suite:** 168/169 pass. Single failure is F-002 (Sherlock Holmes).

---

## Recommended Remediation Order

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 1 | F-001: Barnaby Rudge missing chapters (increase `limit`) | Small | High — silent data loss |
| 2 | F-002: Sherlock Holmes spurious headings (filter front matter) | Medium | Medium — test failure |
| 3 | F-003: CONTENTS text leaking (extend `_is_toc_paragraph`) | Medium | Moderate — search noise |
| 4 | F-005: David Copperfield display (smarter truncation) | Small | Low — readability |
| 5 | F-004: Hard Times front matter noise (min-length filter) | Small | Low — chunk inflation |
| 6 | F-007: Catalog caching | Medium | Low-medium — latency |
