#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${1:-"$ROOT_DIR/dist/ubuntu"}"
PYTHON="${PYTHON:-python3.12}"
PACKAGE="docpull"
MAINTAINER="${MAINTAINER:-Derek Nordgren <derek@dereknordgren.com>}"
HOMEPAGE="https://github.com/dnordgren/docpull"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command '$1' was not found" >&2
    exit 1
  fi
}

require_command "$PYTHON"
require_command dpkg
require_command dpkg-deb
require_command gzip

VERSION="$("$PYTHON" - "$ROOT_DIR/pyproject.toml" <<'PY'
import sys
import tomllib
from pathlib import Path

pyproject = Path(sys.argv[1])
with pyproject.open("rb") as fh:
    data = tomllib.load(fh)
print(data["project"]["version"])
PY
)"

ARCH="${ARCH:-$(dpkg --print-architecture)}"
BUILD_DIR="$(mktemp -d)"
STAGE_DIR="$BUILD_DIR/${PACKAGE}_${VERSION}_${ARCH}"
APP_DIR="$STAGE_DIR/opt/$PACKAGE"
DEBIAN_DIR="$STAGE_DIR/DEBIAN"
DOC_DIR="$STAGE_DIR/usr/share/doc/$PACKAGE"

cleanup() {
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

echo "Building ${PACKAGE}_${VERSION}_${ARCH}.deb"

install -d "$APP_DIR" "$DEBIAN_DIR" "$DOC_DIR" "$STAGE_DIR/usr/bin"
install -d "$OUT_DIR"

"$PYTHON" -m venv --copies "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/venv/bin/python" -m pip install --no-cache-dir "$ROOT_DIR"

cat >"$STAGE_DIR/usr/bin/docpull" <<'EOF'
#!/bin/sh
exec /opt/docpull/venv/bin/python -m docpull_cli "$@"
EOF
chmod 0755 "$STAGE_DIR/usr/bin/docpull"

install -m 0644 "$ROOT_DIR/README.md" "$DOC_DIR/README.md"
install -m 0644 "$ROOT_DIR/LICENSE" "$DOC_DIR/copyright"
cat >"$DOC_DIR/changelog.Debian" <<EOF
docpull (${VERSION}) stable; urgency=medium

  * Build Ubuntu package from upstream version ${VERSION}.

 -- ${MAINTAINER}  $(date -R)
EOF
gzip -9n "$DOC_DIR/changelog.Debian"

INSTALLED_SIZE="$(du -ks "$STAGE_DIR" | awk '{print $1}')"
cat >"$DEBIAN_DIR/control" <<EOF
Package: $PACKAGE
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Installed-Size: $INSTALLED_SIZE
Depends: python3 (>= 3.12), ca-certificates
Homepage: $HOMEPAGE
Description: One-way sync from Google Docs to Markdown
 docpull syncs Google Docs to local Markdown files, including frontmatter,
 multi-tab documents, inline images, and comments as footnotes.
EOF

find "$STAGE_DIR" -type d -exec chmod 0755 {} +
dpkg-deb --root-owner-group --build "$STAGE_DIR" "$OUT_DIR"

echo "Built $OUT_DIR/${PACKAGE}_${VERSION}_${ARCH}.deb"
