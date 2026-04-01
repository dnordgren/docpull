# docpull

One-way sync from Google Docs to Markdown.

## Features

- Converts Google Docs to Markdown with frontmatter
- Multi-tab document support (creates separate files per tab)
- Extracts and downloads inline images
- Converts comments to footnotes
- Multi-account support for different Google accounts
- Atomic file writes for safety

## Installation

### Homebrew (recommended)

```bash
brew install dnordgren/tap/docpull
```

### From source (development)

```bash
git clone https://github.com/dnordgren/docpull.git
cd docpull
uv sync --dev
uv run docpull --help
```

## Setup

### 1. Create Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Docs API** and **Google Drive API**
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the client secrets JSON
6. Save it to `~/.config/docpull/client_secrets.json`

### 2. Configure accounts

On first run, docpull creates a default config at `~/.config/docpull.json`:

```json
{
  "default_account": "personal",
  "accounts": {
    "personal": {
      "email": "",
      "image_dir": "~/Documents/docpull-images/personal"
    }
  }
}
```

Edit this file to:
- Set your email (optional, for reference)
- Configure the image directory where extracted images will be saved
- Add additional accounts if needed

## Usage

```bash
# Sync a document by URL
docpull "https://docs.google.com/document/d/ABC123/edit" --output ~/Documents/my-doc.md

# Sync by document name (searches your Drive)
docpull "My Document Title" --output ~/Documents/my-doc.md

# Use a specific account
docpull "https://..." --output doc.md --account work

# Overwrite without confirmation
docpull "https://..." --output doc.md --force

# Skip image downloads
docpull "https://..." --output doc.md --no-images

# Get agent-optimized usage guide (for AI agents)
docpull --help-agent
```

### Multi-tab documents

For documents with multiple tabs, docpull creates separate files:

```
my-doc-Tab1.md
my-doc-Tab2.md
my-doc-Tab3.md
```

## Output format

Each Markdown file includes YAML frontmatter with metadata:

```yaml
---
title: Document Title
gdoc_id: ABC123...
gdoc_url: https://docs.google.com/document/d/ABC123/edit
account: personal
last_synced: 2024-01-15T10:30:00Z
created: 2024-01-01T09:00:00Z
last_edited: 2024-01-15T10:00:00Z
author: John Doe
---
```

Comments from the Google Doc are converted to footnotes at the end of the document.

## Configuration

### Config file location

- Default: `~/.config/docpull.json`
- Override with `--config /path/to/config.json`

### Credentials location

- Client secrets: `~/.config/docpull/client_secrets.json`
- OAuth tokens: `~/.config/docpull/credentials-{account}.json`

### Multi-account setup

```json
{
  "default_account": "personal",
  "accounts": {
    "personal": {
      "email": "me@gmail.com",
      "image_dir": "~/Documents/docpull-images/personal"
    },
    "work": {
      "email": "me@company.com",
      "image_dir": "~/Documents/docpull-images/work"
    }
  }
}
```

Use `--account work` to sync documents from your work account.

## Development

```bash
git clone https://github.com/dnordgren/docpull.git
cd docpull
uv sync --dev
```

`uv sync --dev` installs the project in editable mode with dev dependencies (pytest).
Changes to `src/` take effect immediately via `uv run docpull`. Run tests with `uv run pytest`.

## License

MIT
