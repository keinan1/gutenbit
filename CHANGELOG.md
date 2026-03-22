# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.14] - 2026-03-22

### Added

- Textualist branding for docs site: gb\* nav mark, red asterisk favicon, brand image in mobile drawer, paper-grain texture, and Textualist style guide color tokens
- Heading rank nesting pass that uses HTML heading hierarchy (h1/h2/h3) as an authoritative structural signal for collected editions
- Single-work title wrapper flattening so chapters in single-work books land at div1 instead of being buried under a redundant wrapper
- Bare Roman numeral TOC links accepted unconditionally as primary structure, removing the previous count threshold
- Recognition of INDUCTION as a dramatic keyword for proper nesting under parent plays
- Embedded ordinal and multi-word index heading recognition for broader TOC detection
- Truncation of TOC sections after apparatus headings (APPENDIX, NOTES ON) to keep commentary flat
- Improved TOC link detection for dense and separator-free table-of-contents entries
- Verse-line div and bare Roman numeral structure detection
- Heading classification, nesting, and rank normalization improvements
- `view --section --forward` extends reading into the next section with enriched footer context
- Project Gutenberg book links and Subjects column in CLI table output
- `link` field in `toc --json` and other JSON payloads for consistency across commands
- Hyperlinked ID column replacing the former Link column in book listings
- `search --book` accepts multiple space-separated book IDs to narrow results
- `books --refresh` accepts optional positional book IDs for targeted refresh
- 33 live battle test regressions for classic Gutenberg works (Dickens, Johnson, Austen, Conrad, and more)
- 18 offline unit tests for new parser features
- 8 additional live battle test regressions for new Gutenberg works
- 20 Johnson/Austen battle tests for note-heading scenarios
- 11 Thackeray and George Eliot battle tests covering collected editions
- Claude Code skills for battle testing, changelog, CLI review, and discovery

### Changed

- Rename `books --update` to `books --refresh` for consistency with `add --refresh` and `catalog --refresh`
- Replace Link column with hyperlinked ID and reorder table columns to ID, Authors, Title, Subjects
- Remove plain-text title truncation from JSON payloads
- Extract hardcoded strings to named constants (`GUTENBERG_ID_LABEL`, `BOOK_LIST_COLUMN_MAX_CHARS`, `BOOK_LIST_SUMMARY_MAX_ITEMS`, `GUTENBERG_CANONICAL_HOST`)
- Docs site styling aligned with Textualist style guide: dark mode via `prefers-color-scheme`, serif italic hero title, simplified branding
- Replace breadcrumb header with compact gb\* nav mark; revert body fonts to Roboto

### Fixed

- Apparatus heading truncation dropping entire works in collected editions (e.g., Henry Esmond losing 2/3 of its content)
- PART ONE not parsed when TOC anchor precedes an intervening title element
- HTML comments leaking into headings and standalone Roman numeral nesting errors
- Note-heading merge bug causing incorrect section boundaries
- Heading-scan fallback skipping earlier peer-rank headings
- Dickens structural parsing: Boz nesting, Mudfog sections, Chuzzlewit descriptions
- Theologico-Political Treatise chapter parsing
- Beowulf battle test filtering on wrong div level
- Search placeholder contrast and light-mode code foreground color in docs
- Drawer logo sizing and visibility issues on mobile
- All ruff and ty lint violations across the codebase

### Performance

- 7.9x parser speedup via heading rank caching and hot-path caching (`_container_residue_without_link_text`, `_is_toc_paragraph`, `_is_toc_context_link`, `_clean_heading_text`)

## [0.1.13] - 2026-03-15

### Added

- Click-based CLI replacing the argparse parser layer, preserving all command names, options, defaults, and help text
- `books --refresh` targeting specific book IDs with optional positional argument
- Multi-book `search --book` filtering with space-separated IDs

### Changed

- Refactor CLI from argparse to Click 8.x with custom `_GutenbitGroup` for consistent help formatting
- Refactor `cli.py` monolith (2,938 lines) into focused submodules: `_cli_helpers`, `_cli_sections`, `_cli_commands`
- Consolidate CLI into `cli/` subpackage mirroring the `html_chunker/` package pattern
- Refactor `html_chunker.py` monolith (2,449 lines) into a package with 5 focused modules (`_constants`, `_scanning`, `_headings`, `_sections`, `__init__`)
- Extract TOC link helpers into dedicated `_toc.py` module
- Extract shared text utilities (`_format_int`, `_single_line`, `_preview`, etc.) into `_text_utils.py`, eliminating 9 duplicated definitions
- Add `_common_options` decorator and `_CommandEnv` dataclass to eliminate repeated option boilerplate
- Add `_with_level()` to `_Section` dataclass, replacing 6+ verbose reconstruction sites
- Rename `_constants.py` to `_common.py` to better reflect its role as shared utilities
- Move opening-line heuristics from `_cli_sections.py` to `_text_utils.py` for better testability
- Move single-use regex patterns to their consuming modules, improving locality
- Make `div_parts_match` and `normalize_div_segment` public; add `__all__` to `cli.py`
- Simplify parameter signatures to use `_DocumentIndex` instead of separate keyword arguments
- Use `O(log n)` bisect lookups in `_find_next_heading` and `_find_non_structural_boundary_after`, replacing `O(n)` DOM traversals
- Reduce technical debt: push SQL filters into queries, consolidate helpers, remove dead code
- Update documentation: tighten language, clarify meaning of chunks

### Fixed

- Type errors and error handling regressions from Click migration (JSON/verbose-aware errors, variable shadowing, type annotations)
- Restore curly quote characters accidentally dropped during refactor
- Remove dead `indexpageno` no-op in `_is_structural_toc_link`
- Remove backward-compatibility `display.py` shim
- Fix help text formatting in all subcommand epilogs with Click `\b` markers

## [0.1.12] - 2026-03-14

### Changed

- Optimize HTML chunker with single-pass DFS document scan replacing 5+ separate DOM traversals — War and Peace: 23% faster, 44% fewer function calls
- Update CLI help copy for default data path messaging

## [0.1.11] - 2026-03-13

### Changed

- Store data in `~/.gutenbit/` instead of cwd-relative `.gutenbit/`, providing a single predictable location for the database and catalog cache

### Fixed

- CLI database path display showing incorrect location

## [0.1.10] - 2026-03-13

### Added

- `toc` command auto-adds missing books and resolves canonical IDs, so users don't need to run `add` first

### Changed

- 1.9x chunker speedup via precomputed heading indices with bisect, single-pass DFS for tag/subtree positions, pre-indexed pagenum spans and img tags — War and Peace: 1.62s to 0.85s

### Fixed

- Preserve source punctuation in structural headings instead of normalizing it away

[Unreleased]: https://github.com/textualist/gutenbit/compare/v0.1.14...HEAD
[0.1.14]: https://github.com/textualist/gutenbit/compare/v0.1.13...v0.1.14
[0.1.13]: https://github.com/textualist/gutenbit/compare/v0.1.12...v0.1.13
[0.1.12]: https://github.com/textualist/gutenbit/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/textualist/gutenbit/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/textualist/gutenbit/compare/v0.1.9...v0.1.10
