"""Google Docs API client wrapper."""

import re
from typing import Dict, List, Optional, Tuple

from googleapiclient.errors import HttpError


class GoogleDocsClient:
    """Client for interacting with Google Docs API."""

    def __init__(self, service):
        """Initialize with authenticated service."""
        self.service = service

    def get_document_id(self, doc_identifier: str) -> str:
        """Extract document ID from URL or return as-is if already an ID.

        Args:
            doc_identifier: Google Doc URL or document ID

        Returns:
            Document ID
        """
        # Pattern: https://docs.google.com/document/d/{DOC_ID}/...
        url_pattern = r'docs\.google\.com/document/d/([a-zA-Z0-9-_]+)'
        match = re.search(url_pattern, doc_identifier)

        if match:
            return match.group(1)

        # Assume it's already a document ID
        return doc_identifier

    def get_document(self, doc_id: str) -> Dict:
        """Fetch full document structure.

        Args:
            doc_id: Google Doc ID

        Returns:
            Document resource dict

        Raises:
            HttpError: If document not found or no access
        """
        try:
            document = self.service.documents().get(
                documentId=doc_id,
                includeTabsContent=True,
                fields='*'
            ).execute()
            return document
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"Document not found: {doc_id}")
            elif e.resp.status == 403:
                raise PermissionError(f"No access to document: {doc_id}")
            elif e.resp.status == 400:
                # Some older documents don't support includeTabsContent; retry without it
                document = self.service.documents().get(
                    documentId=doc_id,
                    fields='*'
                ).execute()
                return document
            else:
                raise

    def get_tabs(self, document: Dict) -> List[Tuple[str, str, List, Dict]]:
        """Extract tabs from document.

        Args:
            document: Document resource dict

        Returns:
            List of (tab_id, tab_name, content, inline_objects) tuples
        """
        tabs = []

        # Check if document has tabs
        if 'tabs' in document:
            for tab in document['tabs']:
                tab_properties = tab.get('tabProperties', {})
                tab_id = tab_properties.get('tabId', '')
                tab_title = tab_properties.get('title', 'Untitled')

                # Get content and inline objects for this tab
                doc_tab = tab.get('documentTab', {})
                content = doc_tab.get('body', {}).get('content', [])
                inline_objects = doc_tab.get('inlineObjects', {})
                tabs.append((tab_id, tab_title, content, inline_objects))
        else:
            # Single-tab document (legacy format)
            content = document.get('body', {}).get('content', [])
            inline_objects = document.get('inlineObjects', {})
            tabs.append(('', 'Main', content, inline_objects))

        return tabs

    def search_documents_by_name(self, drive_service, filename: str) -> Optional[str]:
        """Search for document by name using Drive API.

        Args:
            drive_service: Authenticated Drive service
            filename: Document name to search

        Returns:
            Document ID if found, None otherwise
        """
        try:
            escaped = filename.replace("\\", "\\\\").replace("'", "\\'")
            query = f"name='{escaped}' and mimeType='application/vnd.google-apps.document'"
            results = drive_service.files().list(
                q=query,
                pageSize=10,
                fields="files(id, name)"
            ).execute()

            files = results.get('files', [])

            if not files:
                return None

            if len(files) > 1:
                matches = '\n'.join(
                    f"  https://docs.google.com/document/d/{f['id']}/edit  ({f['name']})"
                    for f in files
                )
                raise ValueError(
                    f"Found {len(files)} documents matching '{filename}'.\n"
                    f"Please re-run with the URL of the one you want:\n{matches}"
                )

            return files[0]['id']
        except HttpError:
            return None
