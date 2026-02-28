"""Frontmatter generation for Markdown files."""

import yaml
from typing import Dict


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
