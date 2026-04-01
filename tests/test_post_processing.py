"""Tests for MarkdownConverter post-processing."""

from docpull_cli.converter import MarkdownConverter


def make_converter():
    return MarkdownConverter(
        document={},
        comments=[],
        image_handler=None,
        drive_client=None,
    )


def test_non_breaking_spaces_are_replaced():
    converter = make_converter()
    result = converter._post_process_markdown("hello\u00a0world")
    assert "\u00a0" not in result
    assert "hello world" in result


def test_curly_quotes_are_straightened():
    converter = make_converter()
    result = converter._post_process_markdown("\u201chello\u201d and \u2018world\u2019")
    assert "\u201c" not in result
    assert "\u201d" not in result
    assert "\u2018" not in result
    assert "\u2019" not in result
    assert '"hello" and \'world\'' in result


def test_dashes_are_normalized():
    converter = make_converter()
    result = converter._post_process_markdown("en\u2013dash and em\u2014dash")
    assert "\u2013" not in result
    assert "\u2014" not in result
    assert "en-dash and em--dash" in result
