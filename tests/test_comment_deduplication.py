"""Tests for comment deduplication in MarkdownConverter."""

import pytest
from docpull_cli.converter import MarkdownConverter


def make_converter(comments):
    """Create a minimal MarkdownConverter with the given comments."""
    return MarkdownConverter(
        document={},
        comments=comments,
        image_handler=None,
        drive_client=None,
    )


def make_comment(comment_id, quote, content="A comment", replies=None):
    return {
        "id": comment_id,
        "anchor": "some-anchor",
        "quotedFileContent": {"value": quote},
        "content": content,
        "author": {"displayName": "Test User"},
        "createdTime": "2026-01-01T00:00:00Z",
        "resolved": False,
        "replies": replies or [],
    }


def test_comment_appears_once_when_quote_matches_multiple_paragraphs():
    """A comment whose quoted text appears in N paragraphs should only be emitted once."""
    comment = make_comment("c1", "middle ground", "Have you considered a middle ground")
    converter = make_converter([comment])

    # Simulate 3 paragraphs all containing the quoted text
    texts = [
        "There is no middle ground here.",
        "Finding a middle ground is hard.",
        "The middle ground approach works best.",
    ]
    results = [converter._add_footnote_for_text(t) for t in texts]

    has_footnote = [had for _, had in results]
    # Only the first match should produce a footnote
    assert has_footnote == [True, False, False]
    assert len(converter.footnotes) == 1
    assert "Have you considered a middle ground" in converter.footnotes[0]


def test_distinct_comments_on_different_paragraphs_both_appear():
    """Two different comments on different paragraphs should each appear once."""
    c1 = make_comment("c1", "scheduling system", "Comment on scheduling")
    c2 = make_comment("c2", "facility management", "Comment on facilities")
    converter = make_converter([c1, c2])

    _, had1 = converter._add_footnote_for_text("The scheduling system design.")
    _, had2 = converter._add_footnote_for_text("The facility management concerns.")

    assert had1 is True
    assert had2 is True
    assert len(converter.footnotes) == 2


def test_two_comments_on_same_paragraph_both_appear_in_one_footnote():
    """Two comments whose quoted text both appear in the same paragraph get one footnote."""
    c1 = make_comment("c1", "scheduling", "First comment")
    c2 = make_comment("c2", "facility", "Second comment")
    converter = make_converter([c1, c2])

    text_with_ref, had = converter._add_footnote_for_text("The scheduling and facility approach.")

    assert had is True
    assert len(converter.footnotes) == 1
    assert "First comment" in converter.footnotes[0]
    assert "Second comment" in converter.footnotes[0]


def test_comment_without_anchor_is_ignored():
    """Comments with no anchor field should not appear in output."""
    comment = {
        "id": "c1",
        "quotedFileContent": {"value": "some text"},
        "content": "Orphaned comment",
        "author": {"displayName": "Test User"},
        "createdTime": "2026-01-01T00:00:00Z",
        "resolved": False,
        "replies": [],
        # no 'anchor' key
    }
    converter = make_converter([comment])

    _, had = converter._add_footnote_for_text("Paragraph with some text in it.")
    assert had is False
    assert len(converter.footnotes) == 0
