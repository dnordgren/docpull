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
