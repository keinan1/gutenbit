"""Tests for paragraph accumulation, kind labelling, and chapter detection."""

from gutenbit.chunker import chunk_text

# ------------------------------------------------------------------
# Basic splitting and accumulation
# ------------------------------------------------------------------


def test_splits_on_blank_lines():
    text = (
        "First paragraph with enough text to pass the minimum length filter easily.\n"
        "\n"
        "Second paragraph also with enough text to pass the minimum length filter here.\n"
    )
    chunks = chunk_text(text)
    paragraphs = [c for c in chunks if c.kind == "paragraph"]
    assert len(paragraphs) == 2
    assert paragraphs[0].content.startswith("First paragraph")
    assert paragraphs[1].content.startswith("Second paragraph")


def test_positions_are_sequential():
    text = "\n\n".join(f"Paragraph {i} has enough content to clear the filter." for i in range(5))
    chunks = chunk_text(text)
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_multiple_blank_lines():
    text = (
        "First paragraph with enough text to be indexed by the chunker module.\n"
        "\n\n\n"
        "Second paragraph with enough text to also be indexed by the chunker.\n"
    )
    chunks = chunk_text(text)
    paragraphs = [c for c in chunks if c.kind == "paragraph"]
    assert len(paragraphs) == 2


def test_empty_text():
    assert chunk_text("") == []


def test_whitespace_only():
    assert chunk_text("   \n\n   \n  ") == []


# ------------------------------------------------------------------
# Accumulation behaviour
# ------------------------------------------------------------------


def test_accumulates_short_blocks():
    """Multiple short blocks are merged into one paragraph chunk."""
    text = "'Hello.'\n\n'Hi there.'\n\n'How are you today?'\n"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].kind == "paragraph"
    assert "'Hello.'" in chunks[0].content
    assert "'Hi there.'" in chunks[0].content
    assert "'How are you today?'" in chunks[0].content
    # Paragraphs joined with double newline
    assert "\n\n" in chunks[0].content


def test_accumulation_emits_at_threshold():
    """Once accumulated text reaches minimum length, a chunk is emitted."""
    text = (
        "This is a real paragraph with enough content to be worth indexing.\n"
        "\n"
        "'Yes,' he said.\n"
        "\n"
        "Another real paragraph with sufficient length to be indexed properly.\n"
    )
    chunks = chunk_text(text)
    # First paragraph is long enough on its own → emitted
    assert chunks[0].kind == "paragraph"
    assert chunks[0].content.startswith("This is a real")
    # "'Yes,' he said." is short but gets accumulated with next paragraph
    assert len(chunks) == 2
    assert "'Yes,' he said." in chunks[1].content
    assert "Another real paragraph" in chunks[1].content


def test_trailing_below_min_emitted_at_section_break():
    """Short text before a heading is emitted as its own chunk."""
    text = (
        "CHAPTER I\n"
        "\n"
        "A long paragraph with enough text to be emitted on its own merits.\n"
        "\n"
        "'My dear.'\n"
        "\n"
        "CHAPTER II\n"
        "\n"
        "Another long paragraph with enough text to be emitted on its own.\n"
    )
    chunks = chunk_text(text)
    kinds = [c.kind for c in chunks]
    assert kinds == ["heading", "paragraph", "paragraph", "heading", "paragraph"]
    assert chunks[2].content == "'My dear.'"
    assert chunks[2].chapter == "CHAPTER I"


def test_trailing_below_min_emitted_at_end():
    """Short text at end of document is emitted as its own chunk."""
    text = "A long paragraph with enough text to be emitted on its own merits.\n\nOk.\n"
    chunks = chunk_text(text)
    assert len(chunks) == 2
    assert chunks[1].content == "Ok."


def test_trailing_below_min_emitted_at_separator():
    """Short text before a separator is emitted as its own chunk."""
    text = (
        "A long paragraph with enough text to be emitted on its own merits.\n"
        "\n"
        "Brief.\n"
        "\n"
        "* * *\n"
        "\n"
        "More text that is long enough to be emitted as a paragraph chunk.\n"
    )
    chunks = chunk_text(text)
    kinds = [c.kind for c in chunks]
    assert kinds == ["paragraph", "paragraph", "separator", "paragraph"]
    assert chunks[1].content == "Brief."


# ------------------------------------------------------------------
# Separators
# ------------------------------------------------------------------


def test_separator_detected():
    text = (
        "Some content that is long enough to pass the minimum length filter.\n"
        "\n"
        "* * *\n"
        "\n"
        "More content that is long enough to pass the minimum length filter.\n"
    )
    chunks = chunk_text(text)
    assert len(chunks) == 3
    assert chunks[1].kind == "separator"
    assert chunks[1].content == "* * *"


def test_separator_variants():
    for sep in ["* * *", "***", "---", "===", "* * * * *", "----------"]:
        text = (
            "Content before the separator is long enough to be a paragraph.\n"
            "\n"
            f"{sep}\n"
            "\n"
            "Content after the separator is long enough to be a paragraph too.\n"
        )
        chunks = chunk_text(text)
        separators = [c for c in chunks if c.kind == "separator"]
        assert len(separators) == 1, f"Expected separator for {sep!r}"


# ------------------------------------------------------------------
# Headings and chapter tracking
# ------------------------------------------------------------------


def test_heading_kind():
    text = (
        "CHAPTER I\n\nIt was a bright cold day in April, and the clocks were striking thirteen.\n"
    )
    chunks = chunk_text(text)
    assert chunks[0].kind == "heading"
    assert chunks[0].content == "CHAPTER I"
    assert chunks[1].kind == "paragraph"


def test_detects_chapter_heading():
    text = (
        "CHAPTER I\n"
        "\n"
        "It was a bright cold day in April, and the clocks were striking thirteen.\n"
        "\n"
        "CHAPTER II\n"
        "\n"
        "Outside, even through the shut window-pane, the world looked cold and bleak.\n"
    )
    chunks = chunk_text(text)
    paragraphs = [c for c in chunks if c.kind == "paragraph"]
    assert len(paragraphs) == 2
    assert paragraphs[0].chapter == "CHAPTER I"
    assert paragraphs[1].chapter == "CHAPTER II"


def test_chapter_label_persists():
    text = (
        "Chapter 1\n"
        "\n"
        "First paragraph of chapter one, long enough to clear the minimum filter.\n"
        "\n"
        "Second paragraph of chapter one, also long enough to clear the filter.\n"
    )
    chunks = chunk_text(text)
    paragraphs = [c for c in chunks if c.kind == "paragraph"]
    assert len(paragraphs) == 2
    assert paragraphs[0].chapter == "Chapter 1"
    assert paragraphs[1].chapter == "Chapter 1"


def test_no_chapter_gives_empty_string():
    text = "A paragraph without any preceding chapter heading, long enough to index.\n"
    chunks = chunk_text(text)
    assert chunks[0].chapter == ""


def test_heading_variants():
    for heading in ["BOOK III", "Part 2", "ACT IV", "SCENE 1", "Section 5"]:
        content = "Some content that is long enough to pass the minimum length filter."
        text = f"{heading}\n\n{content}\n"
        chunks = chunk_text(text)
        heading_chunks = [c for c in chunks if c.kind == "heading"]
        assert len(heading_chunks) == 1
        assert heading_chunks[0].content == heading
        paragraphs = [c for c in chunks if c.kind == "paragraph"]
        assert paragraphs[0].chapter == heading


# ------------------------------------------------------------------
# Reconstruction
# ------------------------------------------------------------------


def test_reconstruct_text_from_chunks():
    """Joining all chunk contents reproduces the original (modulo blank lines)."""
    text = (
        "CHAPTER I\n"
        "\n"
        "'Yes.'\n"
        "\n"
        "A paragraph with enough content to clear the minimum length threshold.\n"
        "\n"
        "* * *\n"
    )
    chunks = chunk_text(text)
    reconstructed = "\n\n".join(c.content for c in chunks)
    assert "CHAPTER I" in reconstructed
    assert "'Yes.'" in reconstructed
    assert "* * *" in reconstructed


def test_all_text_preserved():
    """Nothing is discarded — all text appears in some chunk."""
    text = (
        "CHAPTER I\n"
        "\n"
        "Hi\n"
        "\n"
        "A full paragraph with enough text to be classified as a real paragraph.\n"
        "\n"
        "* * *\n"
        "\n"
        "Ok\n"
    )
    chunks = chunk_text(text)
    reconstructed = "\n\n".join(c.content for c in chunks)
    assert "Hi" in reconstructed
    assert "A full paragraph" in reconstructed
    assert "* * *" in reconstructed
    assert "Ok" in reconstructed
    # Only three kinds exist
    kinds = {c.kind for c in chunks}
    assert kinds <= {"paragraph", "heading", "separator"}


# ------------------------------------------------------------------
# Dickens excerpts — realistic literary structure
# ------------------------------------------------------------------


# Pickwick Papers (PG 580) — chapter opening with quoted speech
_PICKWICK_EXCERPT = """\
CHAPTER I

The first ray of light which illumines the gloom, and converts into a
dazzling brilliancy that obscurity in which the earlier history of the
public career of the immortal Pickwick would appear to be involved, is
derived from the perusal of the following entry in the Transactions of
the Pickwick Club.

'That this Association has heard read, with feelings of unmingled
satisfaction, and unqualified approval, the Paper communicated by
Samuel Pickwick, Esq., G.C.M.P.C.'

* * *

'Mr. Pickwick observed (says the Secretary) that fame was dear to
the heart of every man. Poetic fame was dear to the heart of his
friend Snodgrass; the fame of conquest was equally dear to his
friend Tupman; and the desire of earning fame in the service of
humanity was paramount in his own breast.'
""".strip()


def test_pickwick_excerpt():
    chunks = chunk_text(_PICKWICK_EXCERPT)
    kinds = [c.kind for c in chunks]

    assert kinds == ["heading", "paragraph", "paragraph", "separator", "paragraph"]
    assert chunks[0].content == "CHAPTER I"
    assert all(c.chapter == "CHAPTER I" for c in chunks)
    # All blocks long enough — no accumulation needed
    assert "Pickwick Club" in chunks[1].content
    assert "G.C.M.P.C." in chunks[2].content


# Oliver Twist (PG 730) — chapter with short dialogue lines
_OLIVER_EXCERPT = """\
CHAPTER I

Among other public buildings in a certain town, which for many reasons
it will be prudent to refrain from mentioning, and to which I will
assign no fictitious name, there is one anciently common to most towns,
great or small: to wit, a workhouse.

'What's your name?'

The boy hesitated.

'Oliver Twist.'

'Where do you come from? Who are your parents?'

'I have none, sir.'
""".strip()


def test_oliver_excerpt():
    chunks = chunk_text(_OLIVER_EXCERPT)
    kinds = [c.kind for c in chunks]

    # heading, long paragraph, then two accumulated dialogue groups
    assert kinds == ["heading", "paragraph", "paragraph", "paragraph"]
    assert chunks[0].content == "CHAPTER I"

    # First dialogue group: three short blocks accumulated together
    assert "What's your name?" in chunks[2].content
    assert "The boy hesitated." in chunks[2].content
    assert "Oliver Twist." in chunks[2].content

    # Second dialogue group: two short blocks accumulated together
    assert "Where do you come from?" in chunks[3].content
    assert "I have none, sir." in chunks[3].content

    # Everything is under CHAPTER I
    assert all(c.chapter == "CHAPTER I" for c in chunks)


# Old Curiosity Shop (PG 700) — chapter with dinkus and trailing short text
_CURIOSITY_SHOP_EXCERPT = """\
CHAPTER I

Night is generally my time for walking. In the summer I often leave
home early in the morning, and roam about fields and lanes all day, or
even escape for days or weeks together; but, saving in the country, I
seldom go out until after dark, though, Heaven be thanked, I go abroad
in all seasons.

* * *

'And where do you come from?' I asked.

'Oh, a long way from here,' she replied.

She said no more.
""".strip()


def test_curiosity_shop_excerpt():
    chunks = chunk_text(_CURIOSITY_SHOP_EXCERPT)
    kinds = [c.kind for c in chunks]

    # heading, long para, separator, dialogue pair, trailing narration
    assert kinds == ["heading", "paragraph", "separator", "paragraph", "paragraph"]
    assert chunks[0].content == "CHAPTER I"

    # Dialogue pair accumulated into one chunk
    assert "where do you come from" in chunks[3].content.lower()
    assert "a long way from here" in chunks[3].content

    # Trailing short text emitted as its own chunk (below min, at end-of-doc)
    assert chunks[4].content == "She said no more."


# Nicholas Nickleby (PG 967) — multi-chapter with trailing text at boundaries
_NICKLEBY_EXCERPT = """\
CHAPTER I

There once lived, in a sequestered part of the county of Devonshire,
one Mr. Godfrey Nickleby: a worthy gentleman, who, taking it into his
head rather late in life that he must get married, and not being young
enough or rich enough to aspire to the hand of a lady of fortune,
had wedded an old flame out of mere attachment.

'My dear,' said Mrs. Nickleby.

CHAPTER II

Mr. Ralph Nickleby was not, strictly speaking, what you would call a
merchant, neither was he a banker, nor an attorney, nor a special
pleader, nor a notary. He was certainly not a tradesman, and still
less could he lay any claim to the title of a professional gentleman;
for it would have been impossible to mention any recognised profession
to which he belonged.

---

He was a money-lender.
""".strip()


def test_nickleby_excerpt():
    chunks = chunk_text(_NICKLEBY_EXCERPT)
    kinds = [c.kind for c in chunks]

    # Two chapters with trailing short text at boundaries
    assert kinds == [
        "heading",
        "paragraph",
        "paragraph",  # trailing "'My dear,'" flushed before CHAPTER II
        "heading",
        "paragraph",
        "separator",
        "paragraph",  # trailing "He was a money-lender." at end-of-doc
    ]

    # Chapter labels advance correctly
    assert chunks[2].chapter == "CHAPTER I"
    assert chunks[2].content == "'My dear,' said Mrs. Nickleby."

    assert chunks[6].chapter == "CHAPTER II"
    assert chunks[6].content == "He was a money-lender."

    # Separator detected
    assert chunks[5].kind == "separator"
    assert "---" in chunks[5].content


def test_dickens_all_positions_unique():
    """Across all excerpts, positions are unique and sequential."""
    excerpts = [_PICKWICK_EXCERPT, _OLIVER_EXCERPT, _CURIOSITY_SHOP_EXCERPT, _NICKLEBY_EXCERPT]
    for excerpt in excerpts:
        chunks = chunk_text(excerpt)
        positions = [c.position for c in chunks]
        assert positions == list(range(len(chunks)))


def test_dickens_full_reconstruction():
    """All text can be reconstructed from chunks across all excerpts."""
    excerpts = [_PICKWICK_EXCERPT, _OLIVER_EXCERPT, _CURIOSITY_SHOP_EXCERPT, _NICKLEBY_EXCERPT]
    for excerpt in excerpts:
        chunks = chunk_text(excerpt)
        reconstructed = "\n\n".join(c.content for c in chunks)
        # Every non-blank line from the original should appear in the reconstruction
        for line in excerpt.splitlines():
            line = line.strip()
            if line:
                assert line in reconstructed, f"Missing: {line!r}"
