"""Image extraction and management."""

import hashlib
from pathlib import Path
from typing import Dict, Tuple

import requests
from googleapiclient.errors import HttpError

_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB

class ImageHandler:
    """Handles image extraction and file management."""

    def __init__(self, image_dir: Path, doc_id: str, skip_images: bool = False):
        """Initialize image handler.

        Args:
            image_dir: Directory to save images
            doc_id: Document ID for filename prefix
            skip_images: If True, skip all image downloads
        """
        self.image_dir = Path(image_dir).expanduser()
        self.doc_id = doc_id
        self.skip_images = skip_images
        self.image_cache: Dict[str, str] = {}  # content_hash -> filename

        # Create image directory if needed (skip if not downloading)
        if not skip_images:
            self.image_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/svg+xml': 'svg'
        }
        return mime_to_ext.get(mime_type, 'png')

    def save_image(self, image_data: bytes, mime_type: str = 'image/png') -> Tuple[str, bool]:
        """Save image to disk with deduplication.

        Args:
            image_data: Image bytes
            mime_type: MIME type of image

        Returns:
            Tuple of (relative_path, was_deduplicated)
        """
        # Compute hash for deduplication
        content_hash = self._compute_hash(image_data)

        # Check if already saved
        if content_hash in self.image_cache:
            return (self.image_cache[content_hash], True)

        # Create filename
        ext = self._get_file_extension(mime_type)
        filename = f"{self.doc_id}_{content_hash[:8]}.{ext}"
        filepath = self.image_dir / filename

        # Save image
        with open(filepath, 'wb') as f:
            f.write(image_data)

        # Cache for deduplication
        relative_path = str(filepath)
        self.image_cache[content_hash] = relative_path

        return (relative_path, False)

    def _fetch_image(self, url: str) -> bytes:
        """Download image from URL with safety checks."""
        response = requests.get(url, timeout=30, verify=True)
        response.raise_for_status()
        if len(response.content) > _MAX_IMAGE_BYTES:
            raise ValueError(f"Image exceeds size limit ({len(response.content)} bytes)")
        return response.content

    def download_and_save_image(self, drive_client, inline_object: Dict) -> Tuple[str, bool]:
        """Download inline image from document and save.

        Args:
            drive_client: GoogleDriveClient instance
            inline_object: Inline object properties from document

        Returns:
            Tuple of (image_path, was_deduplicated)
        """
        if self.skip_images:
            raise ValueError("Image download skipped (--no-images)")

        # Extract image properties
        embedded_object = inline_object.get('inlineObjectProperties', {}).get('embeddedObject', {})

        # Try to get image from imageProperties
        image_props = embedded_object.get('imageProperties', {})
        content_uri = image_props.get('contentUri')

        if not content_uri:
            raise ValueError("No content URI found for image")

        # Extract file ID from content URI
        # Format: https://lh3.googleusercontent.com/... or direct Drive link
        if 'drive.google.com' in content_uri or 'docs.google.com' in content_uri:
            # Extract file ID from URL
            import re
            match = re.search(r'id=([a-zA-Z0-9-_]+)', content_uri)
            if match:
                file_id = match.group(1)
                image_data = drive_client.download_image(file_id)
            else:
                image_data = self._fetch_image(content_uri)
        else:
            image_data = self._fetch_image(content_uri)

        # Determine MIME type
        mime_type = image_props.get('sourceUri', '').split('.')[-1]
        if mime_type not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            mime_type = 'image/png'
        else:
            mime_type = f'image/{mime_type}'

        return self.save_image(image_data, mime_type)
