"""Google Drive API client wrapper."""

from datetime import datetime
from typing import Dict, List, Optional

from googleapiclient.errors import HttpError


class GoogleDriveClient:
    """Client for interacting with Google Drive API."""

    def __init__(self, service):
        """Initialize with authenticated service."""
        self.service = service

    def get_file_metadata(self, file_id: str) -> Dict:
        """Fetch file metadata.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dict
        """
        try:
            metadata = self.service.files().get(
                fileId=file_id,
                fields='id,name,createdTime,modifiedTime,owners,lastModifyingUser,sharingUser,webViewLink'
            ).execute()
            return metadata
        except HttpError as e:
            if e.resp.status == 404:
                raise ValueError(f"File not found: {file_id}")
            elif e.resp.status == 403:
                raise PermissionError(f"No access to file: {file_id}")
            else:
                raise

    def get_comments(self, file_id: str) -> List[Dict]:
        """Fetch all comments and replies for a file.

        Args:
            file_id: Google Drive file ID

        Returns:
            List of comment dicts with replies
        """
        try:
            comments = []
            page_token = None

            while True:
                response = self.service.comments().list(
                    fileId=file_id,
                    fields='comments(id,content,author,createdTime,modifiedTime,resolved,quotedFileContent,replies,anchor),nextPageToken',
                    pageToken=page_token,
                    includeDeleted=False
                ).execute()

                comments.extend(response.get('comments', []))

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            return comments
        except HttpError as e:
            if e.resp.status == 403:
                # Comments might be disabled or no access
                return []
            else:
                raise

    def download_image(self, file_id: str) -> bytes:
        """Download an image file.

        Args:
            file_id: Google Drive file ID of the image

        Returns:
            Image bytes
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            return request.execute()
        except HttpError as e:
            raise ValueError(f"Failed to download image {file_id}: {e}")

    def parse_metadata_for_frontmatter(self, metadata: Dict, account_name: str, doc_id: str) -> Dict:
        """Parse Drive metadata into frontmatter dict.

        Args:
            metadata: File metadata from Drive API
            account_name: Account name used for sync
            doc_id: Document ID

        Returns:
            Dict suitable for frontmatter
        """
        frontmatter = {
            'document_title': metadata.get('name', 'Untitled'),
            'gdoc_id': doc_id,
            'gdoc_url': metadata.get('webViewLink', f'https://docs.google.com/document/d/{doc_id}/edit'),
            'account': account_name,
            'last_synced': datetime.utcnow().isoformat() + 'Z'
        }

        # Created time
        if 'createdTime' in metadata:
            frontmatter['created'] = metadata['createdTime']

        # Last edited time
        if 'modifiedTime' in metadata:
            frontmatter['last_edited'] = metadata['modifiedTime']

        # Author (owner)
        owners = metadata.get('owners', [])
        if owners:
            frontmatter['author'] = owners[0].get('displayName', owners[0].get('emailAddress', 'Unknown'))

        # Contributors (last modifying user, sharing user)
        contributors = set()

        if 'lastModifyingUser' in metadata:
            user = metadata['lastModifyingUser']
            name = user.get('displayName', user.get('emailAddress'))
            if name:
                contributors.add(name)

        if 'sharingUser' in metadata:
            user = metadata['sharingUser']
            name = user.get('displayName', user.get('emailAddress'))
            if name:
                contributors.add(name)

        if contributors:
            frontmatter['contributors'] = sorted(list(contributors))

        return frontmatter
