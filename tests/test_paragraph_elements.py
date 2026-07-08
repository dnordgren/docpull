"""Tests for rendering Google Docs paragraph element variants."""

from docpull_cli.converter import MarkdownConverter


def make_converter():
    return MarkdownConverter(
        document={},
        comments=[],
        image_handler=None,
        drive_client=None,
    )


def test_rich_link_renders_title_and_uri():
    element = {
        "richLink": {
            "textStyle": {"bold": True},
            "richLinkProperties": {
                "title": "Project plan",
                "uri": "https://docs.google.com/document/d/example",
                "mimeType": "application/vnd.google-apps.document",
            },
        }
    }

    assert make_converter()._convert_paragraph_element(element) == (
        "[**Project plan**](https://docs.google.com/document/d/example)"
    )


def test_person_uses_email_when_name_is_not_displayed():
    element = {
        "person": {
            "textStyle": {"italic": True},
            "personProperties": {
                "name": "",
                "email": "person@example.com",
            },
        }
    }

    assert make_converter()._convert_paragraph_element(element) == (
        "*person@example.com*"
    )


def test_horizontal_rule_renders_as_markdown_rule():
    paragraph = {
        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        "elements": [{"horizontalRule": {}}],
    }

    assert make_converter()._convert_paragraph(paragraph) == "---\n"


def test_table_cells_reuse_paragraph_element_renderer():
    table = {
        "tableRows": [
            {
                "tableCells": [
                    {
                        "content": [
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "dateElement": {
                                                "dateElementProperties": {
                                                    "displayText": "2026-07-08"
                                                }
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                    {
                        "content": [
                            {
                                "paragraph": {
                                    "elements": [
                                        {
                                            "person": {
                                                "personProperties": {
                                                    "email": "person@example.com"
                                                }
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                ]
            }
        ]
    }

    assert make_converter()._convert_table(table) == (
        "| 2026-07-08 | person@example.com |\n"
        "| --- | --- |\n\n"
    )
