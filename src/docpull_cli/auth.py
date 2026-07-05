"""OAuth authentication for Google APIs with multi-account support."""

import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Required OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]


class AuthManager:
    """Manages OAuth authentication for multiple accounts."""

    def __init__(self, credentials_path: Path, client_secrets_path: Optional[Path] = None):
        """Initialize auth manager.

        Args:
            credentials_path: Path to store/load credentials token
            client_secrets_path: Path to OAuth client secrets JSON
        """
        self.credentials_path = credentials_path
        self.client_secrets_path = client_secrets_path or self._get_default_secrets_path()
        self.credentials: Optional[Credentials] = None

    def _get_default_secrets_path(self) -> Path:
        """Get default path for client secrets."""
        return Path.home() / ".config" / "docpull" / "client_secrets.json"

    def authenticate(self) -> Credentials:
        """Authenticate and return credentials.

        Returns:
            Valid OAuth credentials

        Raises:
            FileNotFoundError: If client secrets file not found
        """
        # Load existing credentials
        if self.credentials_path.exists():
            self.credentials = self._load_credentials()

        # Refresh or create new credentials
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    print("Starting new authentication flow...")
                    self.credentials = self._run_oauth_flow()
            else:
                self.credentials = self._run_oauth_flow()

            # Save credentials
            self._save_credentials()

        return self.credentials

    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from disk, handling legacy pickle files."""
        try:
            data = json.loads(self.credentials_path.read_text())
            os.chmod(self.credentials_path, 0o600)
            return Credentials.from_authorized_user_info(data, SCOPES)
        except (json.JSONDecodeError, ValueError):
            # Legacy pickle file — normalize to JSON immediately after loading.
            import pickle  # noqa: PLC0415
            try:
                with open(self.credentials_path, 'rb') as f:
                    credentials = pickle.load(f)
            except Exception:
                return None

            self.credentials = credentials
            self._save_credentials()
            return credentials

    def _save_credentials(self) -> None:
        """Save credentials to disk as JSON with restrictive permissions."""
        self.credentials_path.write_text(self.credentials.to_json())
        os.chmod(self.credentials_path, 0o600)

    def _run_oauth_flow(self) -> Credentials:
        """Run OAuth flow to get new credentials."""
        if not self.client_secrets_path.exists():
            raise FileNotFoundError(
                f"Client secrets file not found at {self.client_secrets_path}\n\n"
                "To set up authentication:\n"
                "1. Go to https://console.cloud.google.com/\n"
                "2. Create a new project or select existing\n"
                "3. Enable Google Docs API and Google Drive API\n"
                "4. Create OAuth 2.0 credentials (Desktop app)\n"
                "5. Download the client secrets JSON\n"
                f"6. Save it to {self.client_secrets_path}"
            )

        os.chmod(self.client_secrets_path, 0o600)

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secrets_path),
            SCOPES
        )

        credentials = flow.run_local_server(port=0)
        return credentials

    def get_docs_service(self):
        """Get authenticated Google Docs service."""
        if not self.credentials:
            self.authenticate()
        return build('docs', 'v1', credentials=self.credentials)

    def get_drive_service(self):
        """Get authenticated Google Drive service."""
        if not self.credentials:
            self.authenticate()
        return build('drive', 'v3', credentials=self.credentials)
