"""Tests for metadata included in generated YAML frontmatter."""

from docpull_cli.gdrive_client import GoogleDriveClient


def test_frontmatter_uses_document_title_key():
    client = GoogleDriveClient.__new__(GoogleDriveClient)

    frontmatter = client.parse_metadata_for_frontmatter(
        {"name": "Project plan"}, "personal", "document-id"
    )

    assert frontmatter["document_title"] == "Project plan"
    assert "title" not in frontmatter
