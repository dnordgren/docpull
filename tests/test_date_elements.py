"""Tests for Google Docs date smart-chip conversion."""

from docpull_cli.converter import MarkdownConverter


def make_converter():
    return MarkdownConverter(
        document={},
        comments=[],
        image_handler=None,
        drive_client=None,
    )


def test_date_smart_chip_heading_uses_display_text():
    paragraph = {
        "paragraphStyle": {"namedStyleType": "HEADING_2"},
        "elements": [
            {
                "dateElement": {
                    "dateId": "kix.date-chip",
                    "textStyle": {},
                    "dateElementProperties": {
                        "timestamp": "2026-07-07T12:00:00Z",
                        "locale": "en",
                        "dateFormat": "DATE_FORMAT_ISO8601",
                        "timeFormat": "TIME_FORMAT_DISABLED",
                        "displayText": "2026-07-07",
                    },
                }
            },
            {"textRun": {"content": "\n", "textStyle": {}}},
        ],
    }

    assert make_converter()._convert_paragraph(paragraph) == "## 2026-07-07\n"


def test_date_smart_chip_applies_text_style():
    paragraph = {
        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        "elements": [
            {
                "dateElement": {
                    "textStyle": {"bold": True},
                    "dateElementProperties": {"displayText": "July 7, 2026"},
                }
            }
        ],
    }

    assert make_converter()._convert_paragraph(paragraph) == "**July 7, 2026**\n"
