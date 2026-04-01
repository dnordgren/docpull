# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python and dependency management.

```bash
# One-time setup (creates .venv with Python 3.12 + all deps)
uv sync --dev

# Run tests
uv run pytest

# Run the CLI from source
uv run docpull <url> --output <path>
```

The project pins Python 3.12 via `.python-version`. All dependencies (including dev deps like pytest) are managed in `pyproject.toml` and locked in `uv.lock`.

> **Note:** The Homebrew install (`/opt/homebrew/Cellar/docpull/`) is a frozen snapshot of a release build. It does **not** reflect source changes. Always use `uv run docpull` when testing local changes — never edit Homebrew files directly.

## Releasing a New Version

1. **Bump version** in `pyproject.toml`
2. **Merge to main**, then tag and push:
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
3. **Get the tarball sha256** (wait a few seconds after pushing the tag):
   ```bash
   curl -sL https://github.com/dnordgren/docpull/archive/refs/tags/vX.Y.Z.tar.gz | shasum -a 256
   ```
4. **Update `Formula/docpull.rb`** — change `url` and `sha256` to the new values, commit and push to main
5. **Pull the tap** so Homebrew sees the new version:
   ```bash
   git -C $(brew --repository)/Library/Taps/dnordgren/homebrew-docpull pull
   ```
   > Note: `brew update` does not always pull third-party taps automatically. This manual pull is required before `brew upgrade docpull` will detect the new version.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   ```
5. **Verify** - All changes committed
6. **Hand off** - Provide context for next session

**CRITICAL RULES:**

* Work is NOT complete until work is committed, beads synced and validation passing
