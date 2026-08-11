"""Frontmatter generation and parsing for Markdown files."""

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

_GDOC_ID_PATTERN = re.compile(r'docs\.google\.com/document/d/([a-zA-Z0-9-_]+)')


def generate_frontmatter(metadata: Dict) -> str:
    """Generate YAML frontmatter from metadata.

    Args:
        metadata: Dict containing frontmatter fields

    Returns:
        YAML frontmatter string with delimiters
    """
    yaml_content = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )

    return f"---\n{yaml_content}---\n\n"


def parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from Markdown content.

    Args:
        content: Full Markdown file text

    Returns:
        Tuple of (metadata dict or None, body after frontmatter)

    Raises:
        ValueError: If frontmatter delimiters are present but YAML is invalid
    """
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        return None, content

    yaml_lines = []
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            end_idx = i
            break
        yaml_lines.append(line)

    if end_idx is None:
        return None, content

    yaml_text = ''.join(yaml_lines)
    body = ''.join(lines[end_idx + 1:])

    try:
        metadata = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError("YAML frontmatter must be a mapping")

    return metadata, body


def load_frontmatter_from_file(path: str) -> Dict[str, Any]:
    """Load and return frontmatter metadata from a Markdown file.

    Args:
        path: Path to Markdown file

    Returns:
        Frontmatter metadata dict

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If frontmatter is missing or invalid
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    content = file_path.read_text(encoding='utf-8')
    metadata, _ = parse_frontmatter(content)
    if metadata is None:
        raise ValueError(
            f"No YAML frontmatter found in {path}. "
            "Re-pull requires a prior docpull Markdown file."
        )
    return metadata


def resolve_repull_target(metadata: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str]]:
    """Resolve document ID, account, and tab from prior frontmatter.

    Args:
        metadata: Frontmatter dict from a prior docpull file

    Returns:
        Tuple of (gdoc_id, account_or_None, tab_or_None)

    Raises:
        ValueError: If neither gdoc_id nor gdoc_url is present
    """
    gdoc_id = metadata.get('gdoc_id')
    gdoc_url = metadata.get('gdoc_url')
    account = metadata.get('account')
    tab = metadata.get('tab')

    if gdoc_id:
        doc_id = str(gdoc_id).strip()
    elif gdoc_url:
        match = _GDOC_ID_PATTERN.search(str(gdoc_url))
        if not match:
            raise ValueError(
                "Frontmatter has gdoc_url but no document ID could be extracted. "
                "Expected a docs.google.com/document/d/... URL."
            )
        doc_id = match.group(1)
    else:
        raise ValueError(
            "Frontmatter is missing gdoc_id and gdoc_url. "
            "Re-pull requires a prior docpull Markdown file."
        )

    if not doc_id:
        raise ValueError("Frontmatter gdoc_id is empty")

    account_name = str(account).strip() if account else None
    tab_name = str(tab) if tab is not None and str(tab).strip() != '' else None

    return doc_id, account_name, tab_name
