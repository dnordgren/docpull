"""Tests for --repull frontmatter parsing and tab selection."""

import pytest

from docpull_cli.cli import select_tabs_for_repull
from docpull_cli.frontmatter import (
    generate_frontmatter,
    load_frontmatter_from_file,
    parse_frontmatter,
    resolve_repull_target,
)


SAMPLE_FM = {
    "document_title": "Project plan",
    "gdoc_id": "ABC123def456",
    "gdoc_url": "https://docs.google.com/document/d/ABC123def456/edit",
    "account": "personal",
    "last_synced": "2024-01-15T10:30:00Z",
}


def test_parse_frontmatter_roundtrip():
    text = generate_frontmatter(SAMPLE_FM) + "# Body\n\nHello\n"
    metadata, body = parse_frontmatter(text)
    assert metadata["gdoc_id"] == "ABC123def456"
    assert metadata["account"] == "personal"
    assert body.lstrip().startswith("# Body")


def test_parse_frontmatter_missing_returns_none():
    metadata, body = parse_frontmatter("# Just markdown\n")
    assert metadata is None
    assert body.startswith("# Just markdown")


def test_parse_frontmatter_invalid_yaml():
    content = "---\n: bad: [unclosed\n---\nbody\n"
    with pytest.raises(ValueError, match="Invalid YAML"):
        parse_frontmatter(content)


def test_parse_frontmatter_non_mapping():
    content = "---\n- item\n- other\n---\nbody\n"
    with pytest.raises(ValueError, match="mapping"):
        parse_frontmatter(content)


def test_resolve_repull_from_gdoc_id():
    doc_id, account, tab = resolve_repull_target(SAMPLE_FM)
    assert doc_id == "ABC123def456"
    assert account == "personal"
    assert tab is None


def test_resolve_repull_from_gdoc_url_only():
    metadata = {
        "gdoc_url": "https://docs.google.com/document/d/URLONLY99/edit?usp=sharing",
        "account": "work",
        "tab": "Overview",
    }
    doc_id, account, tab = resolve_repull_target(metadata)
    assert doc_id == "URLONLY99"
    assert account == "work"
    assert tab == "Overview"


def test_resolve_repull_prefers_gdoc_id():
    metadata = {
        "gdoc_id": "ID-PRIMARY",
        "gdoc_url": "https://docs.google.com/document/d/URL-SECONDARY/edit",
    }
    doc_id, account, tab = resolve_repull_target(metadata)
    assert doc_id == "ID-PRIMARY"
    assert account is None
    assert tab is None


def test_resolve_repull_missing_ids():
    with pytest.raises(ValueError, match="gdoc_id and gdoc_url"):
        resolve_repull_target({"document_title": "Nope"})


def test_resolve_repull_bad_url():
    with pytest.raises(ValueError, match="no document ID"):
        resolve_repull_target({"gdoc_url": "https://example.com/not-a-doc"})


def test_load_frontmatter_from_file(tmp_path):
    path = tmp_path / "prior.md"
    path.write_text(generate_frontmatter(SAMPLE_FM) + "content\n", encoding="utf-8")
    loaded = load_frontmatter_from_file(str(path))
    assert loaded["gdoc_id"] == "ABC123def456"


def test_load_frontmatter_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_frontmatter_from_file(str(tmp_path / "missing.md"))


def test_load_frontmatter_no_yaml(tmp_path):
    path = tmp_path / "plain.md"
    path.write_text("# plain\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No YAML frontmatter"):
        load_frontmatter_from_file(str(path))


def test_select_tabs_for_repull_all():
    tabs = [
        ("t1", "One", [], {}),
        ("t2", "Two", [], {}),
    ]
    assert select_tabs_for_repull(tabs, None) == tabs


def test_select_tabs_for_repull_named():
    tabs = [
        ("t1", "One", [1], {}),
        ("t2", "Two", [2], {}),
    ]
    selected = select_tabs_for_repull(tabs, "Two")
    assert len(selected) == 1
    assert selected[0][1] == "Two"
    assert selected[0][2] == [2]


def test_select_tabs_for_repull_missing():
    tabs = [("t1", "One", [], {})]
    with pytest.raises(ValueError, match="not found"):
        select_tabs_for_repull(tabs, "Missing")
