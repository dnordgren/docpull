"""Tests for headless credential setup and non-interactive CLI paths."""

import base64
import io
import json
import os
import pickle
import stat

from google.oauth2.credentials import Credentials

from docpull_cli.auth import AuthManager, SCOPES
from docpull_cli.cli import AGENT_HELP, check_existing_files
from docpull_cli.config import Config


def file_mode(path):
    """Return only the permission bits for a path."""
    return stat.S_IMODE(path.stat().st_mode)


def test_config_bootstraps_missing_credentials_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    credentials = {"token": "token", "refresh_token": "refresh"}
    client_secrets = {"installed": {"client_id": "id", "client_secret": "secret"}}

    monkeypatch.setenv(
        "DOCPULL_CREDENTIALS_PERSONAL_B64",
        base64.b64encode(json.dumps(credentials).encode()).decode(),
    )
    monkeypatch.setenv(
        "DOCPULL_CLIENT_SECRETS_B64",
        base64.b64encode(json.dumps(client_secrets).encode()).decode(),
    )

    Config(str(tmp_path / "docpull.json"))

    docpull_dir = tmp_path / ".config" / "docpull"
    credentials_path = docpull_dir / "credentials-personal.json"
    client_secrets_path = docpull_dir / "client_secrets.json"

    assert json.loads(credentials_path.read_text()) == credentials
    assert json.loads(client_secrets_path.read_text()) == client_secrets
    assert file_mode(credentials_path) == 0o600
    assert file_mode(client_secrets_path) == 0o600


def test_config_does_not_overwrite_existing_env_seeded_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    docpull_dir = tmp_path / ".config" / "docpull"
    docpull_dir.mkdir(parents=True)
    credentials_path = docpull_dir / "credentials-personal.json"
    credentials_path.write_text('{"token": "existing"}')
    os.chmod(credentials_path, 0o644)

    monkeypatch.setenv(
        "DOCPULL_CREDENTIALS_PERSONAL_B64",
        base64.b64encode(b'{"token": "from-env"}').decode(),
    )

    Config(str(tmp_path / "docpull.json"))

    assert json.loads(credentials_path.read_text()) == {"token": "existing"}
    assert file_mode(credentials_path) == 0o600


def test_pickle_credentials_are_migrated_to_json_on_load(tmp_path):
    credentials_path = tmp_path / "credentials-personal.json"
    original = Credentials(
        token="token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.example/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=SCOPES,
    )
    credentials_path.write_bytes(pickle.dumps(original))

    loaded = AuthManager(credentials_path)._load_credentials()

    assert loaded.token == "token"
    migrated = json.loads(credentials_path.read_text())
    assert migrated["token"] == "token"
    assert migrated["refresh_token"] == "refresh-token"
    assert file_mode(credentials_path) == 0o600


def test_check_existing_files_reports_clean_error_without_stdin(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "existing.md"
    output_path.write_text("already here")
    monkeypatch.setattr("sys.stdin", io.StringIO(""))

    assert check_existing_files([str(output_path)], force=False) is False

    captured = capsys.readouterr()
    assert "Output file exists" in captured.err
    assert "pass --force" in captured.err


def test_help_agent_documents_env_credential_seeding():
    assert "DOCPULL_CLIENT_SECRETS_B64" in AGENT_HELP
    assert "DOCPULL_CREDENTIALS_<ACCOUNT>_B64" in AGENT_HELP
    assert "single-line base64" in AGENT_HELP
