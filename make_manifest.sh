#!/usr/bin/env bash
# Regenerate MANIFEST.sha256 for the release.
# Run from the repository root, immediately before tagging.
set -euo pipefail
cd "$(dirname "$0")"
find . -type f \
  ! -name 'MANIFEST.sha256' \
  ! -path './.git/*' \
  ! -path '*__pycache__*' \
  ! -name '*.pyc' \
  ! -name '.DS_Store' \
  -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
echo "MANIFEST.sha256 written: $(wc -l < MANIFEST.sha256) files"
echo "Verify any copy with:  sha256sum -c MANIFEST.sha256"
