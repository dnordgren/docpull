#!/usr/bin/env python3
"""Main CLI entry point for docpull."""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

from .auth import AuthManager
from .config import Config
from .converter import MarkdownConverter
from .frontmatter import generate_frontmatter
from .gdocs_client import GoogleDocsClient
from .gdrive_client import GoogleDriveClient
from .image_handler import ImageHandler

def sanitize_filename(name: str) -> str:
    """Sanitize tab name for use in filename.

    Args:
        name: Tab name

    Returns:
        Sanitized filename component
    """
    # Remove or replace invalid filename characters
    name = name.replace('/', '-').replace('\\', '-')
    name = ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
    return name.strip()

def generate_output_filenames(base_output: str, tabs: List[Tuple[str, str, List, dict]]) -> List[Tuple[str, str, List, dict]]:
    """Generate output filenames for each tab.

    Args:
        base_output: Base output filename from --output
        tabs: List of (tab_id, tab_name, content, inline_objects) tuples

    Returns:
        List of (output_path, tab_name, content, inline_objects) tuples
    """
    if len(tabs) == 1:
        # Single tab - use base output name
        return [(base_output, tabs[0][1], tabs[0][2], tabs[0][3])]

    # Multi-tab document
    base_path = Path(base_output)
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    result = []
    seen_names = set()

    for tab_id, tab_name, content, inline_objects in tabs:
        safe_name = sanitize_filename(tab_name)

        # Handle duplicate tab names
        unique_name = safe_name
        counter = 2
        while unique_name in seen_names:
            unique_name = f"{safe_name}-{counter}"
            counter += 1

        seen_names.add(unique_name)
        output_path = str(parent / f"{stem}-{unique_name}{suffix}")
        result.append((output_path, tab_name, content, inline_objects))

    return result

def check_existing_files(output_paths: List[str], force: bool) -> bool:
    """Check if output files exist and prompt if needed.

    Args:
        output_paths: List of output file paths
        force: If True, skip prompts

    Returns:
        True to proceed, False to cancel
    """
    existing = [p for p in output_paths if Path(p).exists()]

    if not existing:
        return True

    if force:
        return True

    print(f"\nThe following file(s) already exist:")
    for path in existing:
        print(f"  - {path}")

    response = input("\nOverwrite? [y/N]: ").strip().lower()
    return response in ('y', 'yes')

def write_markdown_file(output_path: str, frontmatter: str, content: str) -> None:
    """Write Markdown file atomically.

    Args:
        output_path: Output file path
        frontmatter: YAML frontmatter
        content: Markdown content
    """
    full_content = frontmatter + content

    # Write to temp file first
    output_path_obj = Path(output_path)
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=output_path_obj.parent,
        delete=False
    ) as tmp_file:
        tmp_file.write(full_content)
        tmp_path = tmp_file.name

    # Atomic rename
    Path(tmp_path).replace(output_path_obj)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Sync Google Docs to Markdown with multi-tab support'
    )
    parser.add_argument(
        'doc',
        help='Google Doc filename or URL'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output Markdown file path'
    )
    parser.add_argument(
        '--account',
        help='Account name (defaults to config default)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite without confirmation'
    )
    parser.add_argument(
        '--config',
        help='Path to config file (default: ~/.config/docpull.json)'
    )
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Skip downloading inline images'
    )

    args = parser.parse_args()

    try:
        # Load config
        config = Config(args.config)
        account = config.get_account(args.account)
        account_name = account['name']

        print(f"Authenticating with Google (account: {account_name})...")

        # Authenticate
        creds_path = config.get_credentials_path(account_name)
        auth_manager = AuthManager(creds_path)
        auth_manager.authenticate()

        print("✓ Authentication successful\n")

        # Get API services
        docs_service = auth_manager.get_docs_service()
        drive_service = auth_manager.get_drive_service()

        # Initialize clients
        docs_client = GoogleDocsClient(docs_service)
        drive_client = GoogleDriveClient(drive_service)

        # Get document ID
        print(f"Fetching document \"{args.doc}\"...")

        # Try to parse as URL first, then search by name
        if 'docs.google.com' in args.doc:
            doc_id = docs_client.get_document_id(args.doc)
        else:
            doc_id = docs_client.search_documents_by_name(drive_service, args.doc)
            if not doc_id:
                print(f"Error: No document found matching '{args.doc}'.")
                print("Check the name or re-run with the full document URL instead.")
                sys.exit(1)

        # Fetch document
        document = docs_client.get_document(doc_id)

        # Get tabs
        tabs = docs_client.get_tabs(document)

        # Fetch metadata and comments
        metadata = drive_client.get_file_metadata(doc_id)
        comments = drive_client.get_comments(doc_id)

        print(f"✓ Found document ({len(tabs)} tab(s), {len(comments)} comment(s))\n")

        # Generate output filenames
        output_files = generate_output_filenames(args.output, tabs)
        output_paths = [path for path, _, _, _ in output_files]

        # Check existing files
        if not check_existing_files(output_paths, args.force):
            print("Cancelled")
            sys.exit(0)

        # Convert each tab
        print("Converting to Markdown...")

        image_dir = config.get_image_dir(account_name)
        image_handler = ImageHandler(image_dir, doc_id, skip_images=args.no_images)

        files_created = []

        for output_path, tab_name, content, inline_objects in output_files:
            # Generate frontmatter
            fm_data = drive_client.parse_metadata_for_frontmatter(metadata, account_name, doc_id)
            if len(tabs) > 1:
                fm_data['tab'] = tab_name
            frontmatter = generate_frontmatter(fm_data)

            # Convert content
            converter = MarkdownConverter(document, comments, image_handler, drive_client, inline_objects)
            markdown_content = converter.convert_content(content)

            # Write file
            write_markdown_file(output_path, frontmatter, markdown_content)
            files_created.append((output_path, tab_name))

            print(f"✓ {output_path} (Tab: {tab_name})")

        # Summary
        total_images = len(image_handler.image_cache)
        deduplicated = sum(1 for _, was_dedup in image_handler.image_cache.items() if was_dedup)

        if total_images > 0:
            print(f"\nExtracting images to {image_dir}...")
            print(f"✓ Downloaded {total_images} image(s)" + (f" ({deduplicated} deduplicated)" if deduplicated > 0 else ""))

        print("\n" + "=" * 40)
        print("Sync complete!")
        print(f"  Files created: {len(files_created)}")
        if total_images > 0:
            print(f"  Images extracted: {total_images}")
        if comments:
            print(f"  Comments converted: {len(comments)}")
        print("=" * 40)

    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
