"""Convert Google Docs structure to Markdown."""

import html
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .image_handler import ImageHandler


class MarkdownConverter:
    """Converts Google Docs structure to Markdown."""

    def __init__(self, document: Dict, comments: List[Dict], image_handler: ImageHandler, drive_client, inline_objects: Dict = None):
        """Initialize converter.

        Args:
            document: Full document structure from Docs API
            comments: List of comments from Drive API
            image_handler: ImageHandler instance
            drive_client: GoogleDriveClient instance
            inline_objects: Inline objects dict (images) for this tab
        """
        self.document = document
        self.comments = comments
        self.image_handler = image_handler
        self.drive_client = drive_client

        # Build comment map by anchor/position
        self.comment_map = self._build_comment_map()
        self.footnote_counter = 1
        self.footnotes: List[str] = []
        self._emitted_comment_ids: set = set()

        # Track inline objects (images) - use provided or fall back to document-level
        self.inline_objects = inline_objects if inline_objects is not None else document.get('inlineObjects', {})

    def _build_comment_map(self) -> Dict[str, List[Dict]]:
        """Build map of text positions to comments."""
        comment_map = {}

        for comment in self.comments:
            # Get anchor information
            anchor = comment.get('anchor')
            if not anchor:
                continue

            # Anchor can be a text range or specific position
            quoted = comment.get('quotedFileContent', {})
            quote = html.unescape(quoted.get('value', ''))

            # Use quote as key for matching
            if quote:
                if quote not in comment_map:
                    comment_map[quote] = []
                comment_map[quote].append(comment)

        return comment_map

    def _format_comment_as_footnote(self, comment: Dict) -> str:
        """Format comment and replies as footnote text.

        Args:
            comment: Comment dict from Drive API

        Returns:
            Formatted footnote text
        """
        parts = []

        # Main comment
        author = comment.get('author', {}).get('displayName', 'Unknown')
        created = comment.get('createdTime', '')
        content = comment.get('content', '').strip()
        resolved = comment.get('resolved', False)

        # Format date
        date_str = created.split('T')[0] if created else ''

        # Build main comment text
        status = "RESOLVED" if resolved else ""
        header = f"@{author} ({date_str}" + (f", {status}" if status else "") + ")"
        parts.append(f"-{header}: {content}")

        # Add replies
        replies = comment.get('replies', [])
        for reply in replies:
            reply_author = reply.get('author', {}).get('displayName', 'Unknown')
            reply_content = reply.get('content', '').strip()
            reply_created = reply.get('createdTime', '')
            reply_date = reply_created.split('T')[0] if reply_created else ''

            parts.append(f"-@{reply_author} ({reply_date}): {reply_content}")

        return '\n'.join(parts)

    def _add_footnote_for_text(self, text: str) -> Tuple[str, bool]:
        """Check if text has comments and add footnote reference.

        Args:
            text: Text content to check

        Returns:
            Tuple of (text_with_footnote, has_footnote)
        """
        # Look for matching comments, skipping any already emitted
        matching_comments = []

        for quote, comments in self.comment_map.items():
            if quote in text:
                for comment in comments:
                    comment_id = comment.get('id')
                    if comment_id not in self._emitted_comment_ids:
                        matching_comments.append(comment)

        if not matching_comments:
            return (text, False)

        # Mark these comments as emitted
        for comment in matching_comments:
            self._emitted_comment_ids.add(comment.get('id'))

        # Add footnote reference
        footnote_ref = f"[^{self.footnote_counter}]"
        text_with_footnote = text + footnote_ref

        # Generate footnote content
        footnote_parts = []
        for comment in matching_comments:
            footnote_parts.append(self._format_comment_as_footnote(comment))

        self.footnotes.append(f"[^{self.footnote_counter}]: " + '\n'.join(footnote_parts))
        self.footnote_counter += 1

        return (text_with_footnote, True)

    def _is_ordered_list(self, list_id: str, nesting_level: int) -> bool:
        """Return True if the list at this nesting level uses ordered glyphs."""
        ordered_glyph_types = {'DECIMAL', 'ALPHA', 'UPPER_ALPHA', 'ROMAN', 'UPPER_ROMAN'}
        lists = self.document.get('lists', {})
        levels = lists.get(list_id, {}).get('listProperties', {}).get('nestingLevels', [])
        if nesting_level < len(levels):
            glyph_type = levels[nesting_level].get('glyphType', '')
            return glyph_type in ordered_glyph_types
        return False

    def _apply_text_style(self, text: str, text_style: Dict) -> str:
        """Apply text formatting to text.

        Args:
            text: Plain text
            text_style: Text style dict from Docs API

        Returns:
            Markdown-formatted text
        """
        if not text_style:
            return text

        # Bold
        if text_style.get('bold'):
            text = f"**{text}**"

        # Italic
        if text_style.get('italic'):
            text = f"*{text}*"

        # Code (using monospace font as proxy)
        if text_style.get('weightedFontFamily', {}).get('fontFamily') == 'Courier New':
            text = f"`{text}`"

        # Strikethrough (not standard Markdown, but some parsers support it)
        if text_style.get('strikethrough'):
            text = f"~~{text}~~"

        # Links
        if 'link' in text_style:
            url = text_style['link'].get('url', '')
            if url:
                text = f"[{text}]({url})"

        return text

    def _convert_paragraph_element(self, element: Dict) -> str:
        """Convert one Google Docs paragraph element to Markdown."""
        if 'textRun' in element:
            text_run = element['textRun']
            text = text_run.get('content', '')

            # Strip trailing newlines before styling so markers do not wrap them.
            trailing_newlines = text[len(text.rstrip('\n')):]
            text = text.rstrip('\n')
            return self._apply_text_style(
                text,
                text_run.get('textStyle', {}),
            ) + trailing_newlines

        if 'person' in element:
            person = element['person']
            properties = person.get('personProperties', {})
            display_text = properties.get('name') or properties.get('email', '')
            return self._apply_text_style(
                display_text,
                person.get('textStyle', {}),
            )

        if 'richLink' in element:
            rich_link = element['richLink']
            properties = rich_link.get('richLinkProperties', {})
            title = properties.get('title', '')
            uri = properties.get('uri', '')
            if not title:
                return uri

            # The rich-link URI is rendered explicitly below; avoid applying a
            # duplicate link if Google also includes one in textStyle.
            text_style = {
                key: value
                for key, value in rich_link.get('textStyle', {}).items()
                if key != 'link'
            }
            title = self._apply_text_style(title, text_style)
            return f"[{title}]({uri})" if uri else title

        if 'dateElement' in element:
            date_element = element['dateElement']
            display_text = date_element.get(
                'dateElementProperties',
                {},
            ).get('displayText', '')
            return self._apply_text_style(
                display_text,
                date_element.get('textStyle', {}),
            )

        if 'horizontalRule' in element:
            return '---'

        if 'inlineObjectElement' in element:
            inline_obj_id = element['inlineObjectElement'].get('inlineObjectId')
            if not inline_obj_id or inline_obj_id not in self.inline_objects:
                return ''

            try:
                image_path, _ = self.image_handler.download_and_save_image(
                    self.drive_client,
                    self.inline_objects[inline_obj_id],
                )
                # Use ~ for home directory
                if image_path.startswith(str(self.image_handler.image_dir.parent.parent)):
                    image_path = image_path.replace(
                        str(self.image_handler.image_dir.parent.parent),
                        '~',
                    )
                return f"![image]({image_path})"
            except Exception as e:
                print(f"Warning: Failed to process image {inline_obj_id}: {e}")
                return f"[Image: {inline_obj_id}]"

        return ''

    def _convert_paragraph(self, paragraph: Dict) -> str:
        """Convert paragraph element to Markdown.

        Args:
            paragraph: Paragraph dict from Docs API

        Returns:
            Markdown paragraph text
        """
        elements = paragraph.get('elements', paragraph.get('paragraphElements', []))
        para_style = paragraph.get('paragraphStyle', {})

        # Determine paragraph type
        named_style = para_style.get('namedStyleType', 'NORMAL_TEXT')

        # Build text content
        full_text = ''.join(
            self._convert_paragraph_element(element)
            for element in elements
        ).rstrip()

        # Check for comments on this text
        full_text, _ = self._add_footnote_for_text(full_text)

        # List item — check for bullet before style
        bullet = paragraph.get('bullet')
        if bullet:
            nesting = bullet.get('nestingLevel', 0)
            indent = '  ' * nesting
            list_id = bullet.get('listId', '')
            # Determine ordered vs unordered
            ordered = self._is_ordered_list(list_id, nesting)
            prefix = '1.' if ordered else '*'
            if not full_text or full_text == '\n':
                return '\n'
            return f"{indent}{prefix} {full_text}\n"

        # Format based on style
        if named_style == 'HEADING_1':
            return f"# {full_text}\n"
        elif named_style == 'HEADING_2':
            return f"## {full_text}\n"
        elif named_style == 'HEADING_3':
            return f"### {full_text}\n"
        elif named_style == 'HEADING_4':
            return f"#### {full_text}\n"
        elif named_style == 'HEADING_5':
            return f"##### {full_text}\n"
        elif named_style == 'HEADING_6':
            return f"###### {full_text}\n"
        elif named_style == 'SUBTITLE':
            return f"## {full_text}\n"
        elif named_style == 'TITLE':
            return f"# {full_text}\n"
        else:
            # Regular paragraph
            if not full_text or full_text == '\n':
                return '\n'
            return f"{full_text}\n"

    def _convert_list(self, content: List[Dict], start_index: int) -> Tuple[str, int]:
        """Convert list elements to Markdown.

        Args:
            content: List of content elements
            start_index: Starting index in content list

        Returns:
            Tuple of (markdown_text, next_index)
        """
        # This is simplified - proper list handling requires tracking nesting levels
        # and list IDs across paragraphs
        return ('', start_index)

    def _convert_table(self, table: Dict) -> str:
        """Convert table to Markdown.

        Args:
            table: Table dict from Docs API

        Returns:
            Markdown table text
        """
        rows = table.get('tableRows', [])
        if not rows:
            return ''

        md_lines = []

        for row_idx, row in enumerate(rows):
            cells = row.get('tableCells', [])
            cell_texts = []

            for cell in cells:
                # Extract text from cell content
                cell_content = cell.get('content', [])
                cell_text = ''
                for element in cell_content:
                    if 'paragraph' in element:
                        para_elements = element['paragraph'].get('elements', element['paragraph'].get('paragraphElements', []))
                        cell_text += ''.join(
                            self._convert_paragraph_element(para_elem)
                            for para_elem in para_elements
                        )

                cell_texts.append(cell_text.strip())

            # Build row
            md_lines.append('| ' + ' | '.join(cell_texts) + ' |')

            # Add separator after header row
            if row_idx == 0:
                md_lines.append('| ' + ' | '.join(['---'] * len(cell_texts)) + ' |')

        return '\n'.join(md_lines) + '\n\n'

    def _post_process_markdown(self, text: str) -> str:
        """Post-process markdown for linter compliance.

        Handles:
          MD004: asterisk bullets (done at emit time)
          MD012: no consecutive blank lines
          MD022: blank lines around headings
          MD032: blank lines around list blocks
          MD047: single trailing newline
        """
        def is_heading(s):
            return bool(re.match(r'^#{1,6} ', s))

        def is_list_item(s):
            return bool(re.match(r'^\s*[\*\-\+] |^\s*\d+\. ', s))

        def is_blank(s):
            return s.strip() == ''

        text = text.replace('\u00a0', ' ')
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        text = text.replace('\u2013', '-').replace('\u2014', '--')
        text = text.replace('\u201c', '"').replace('\u201d', '"')

        lines = text.split('\n')
        out = []

        for i, line in enumerate(lines):
            next_line = lines[i + 1] if i + 1 < len(lines) else ''
            prev = out[-1] if out else ''

            # MD022: blank line before heading
            if is_heading(line) and out and not is_blank(prev):
                out.append('')

            # MD032: blank line before start of a list block
            if is_list_item(line) and out and not is_blank(prev) and not is_list_item(prev):
                out.append('')

            out.append(line)

            # MD022: blank line after heading
            if is_heading(line) and not is_blank(next_line):
                out.append('')

            # MD032: blank line after end of a list block
            if is_list_item(line) and not is_list_item(next_line) and not is_blank(next_line) and next_line != '':
                out.append('')

        # MD012: collapse consecutive blank lines into one
        collapsed = []
        prev_blank = False
        for line in out:
            blank = is_blank(line)
            if blank and prev_blank:
                continue
            collapsed.append(line)
            prev_blank = blank

        # MD047: single trailing newline
        result = '\n'.join(collapsed).rstrip('\n') + '\n'
        return result

    def convert_content(self, content: List[Dict]) -> str:
        """Convert document content to Markdown.

        Args:
            content: List of content elements

        Returns:
            Markdown text
        """
        self.footnotes = []
        self.footnote_counter = 1

        md_parts = []

        for element in content:
            if 'paragraph' in element:
                md_parts.append(self._convert_paragraph(element['paragraph']))

            elif 'table' in element:
                md_parts.append(self._convert_table(element['table']))

            elif 'sectionBreak' in element:
                section_type = element['sectionBreak'].get('sectionStyle', {}).get('sectionType', '')
                if section_type not in ('CONTINUOUS', ''):
                    md_parts.append('\n---\n\n')

        # Join content
        markdown = ''.join(md_parts)

        # Add footnotes at the end
        if self.footnotes:
            markdown += '\n\n' + '\n\n'.join(self.footnotes) + '\n'

        return self._post_process_markdown(markdown)
