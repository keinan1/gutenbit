"""Tests for Project Gutenberg header/footer stripping."""

from gutenbit.download import strip_headers


def test_standard_gutenberg_format():
    text = (
        "The Project Gutenberg eBook of Test Book\n"
        "\n"
        "Produced by Someone\n"
        "\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK TEST BOOK ***\n"
        "\n"
        "Chapter 1\n"
        "\n"
        "It was a dark and stormy night.\n"
        "\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK TEST BOOK ***\n"
        "\n"
        "End of Project Gutenberg's Test Book\n"
    )
    result = strip_headers(text)
    assert result == "Chapter 1\n\nIt was a dark and stormy night."


def test_preserves_all_internal_content():
    text = (
        "*** START OF THE PROJECT GUTENBERG EBOOK FOO ***\n"
        "\n"
        "Line one.\n"
        "Line two.\n"
        "Line three.\n"
        "\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK FOO ***\n"
    )
    result = strip_headers(text)
    assert result == "Line one.\nLine two.\nLine three."


def test_no_markers_returns_original():
    text = "Just some plain text.\nNothing special here."
    assert strip_headers(text) == text


def test_case_insensitive_markers():
    text = (
        "*** Start Of The Project Gutenberg Ebook Test ***\n"
        "\n"
        "Content here.\n"
        "\n"
        "*** End Of The Project Gutenberg Ebook Test ***\n"
    )
    result = strip_headers(text)
    assert result == "Content here."


def test_only_start_marker():
    text = (
        "Some preamble.\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK TITLE ***\n"
        "\n"
        "The actual book content.\n"
        "More content.\n"
    )
    result = strip_headers(text)
    assert result == "The actual book content.\nMore content."


def test_strips_leading_trailing_whitespace():
    text = (
        "*** START OF THE PROJECT GUTENBERG EBOOK X ***\n"
        "\n"
        "\n"
        "  Content with spaces.  \n"
        "\n"
        "\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK X ***\n"
    )
    result = strip_headers(text)
    assert result == "Content with spaces."
