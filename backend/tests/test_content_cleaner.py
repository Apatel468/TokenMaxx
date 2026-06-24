"""Tests for scraped content cleaning."""

from services.content_cleaner import clean_content


def test_removes_duplicate_whitespace():
    result = clean_content("Title", "Hello    world\n\n\n\nTest")
    assert "Hello world" in result.content
    assert "\n\n\n" not in result.content


def test_strips_cookie_boilerplate():
    result = clean_content(
        "Page",
        "Main article text here.\nAccept all cookies\nPrivacy Policy\nMore content.",
    )
    assert "cookie" not in result.content.lower()
    assert "Main article text" in result.content


def test_truncates_oversized_content():
    long_text = "word " * 5000
    result = clean_content("Big", long_text, max_chars=500)
    assert len(result.content) <= 520
    assert "[Content truncated]" in result.content


def test_word_count():
    result = clean_content("T", "one two three")
    assert result.word_count == 3
