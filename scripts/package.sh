#!/usr/bin/env bash
# Builds dist/FactopiaVoice-<version>.zip from the last commit.
# Uses git archive, so only committed files are included, and the folders
# marked export-ignore in .gitattributes (tests, docs, CI) are left out.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' factopia_voice/__init__.py)
if [ -z "$version" ]; then
  echo "Could not read __version__ from factopia_voice/__init__.py" >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "Note: uncommitted changes are not included in the zip." >&2
fi

mkdir -p dist
out="dist/FactopiaVoice-$version.zip"
git archive --format=zip --prefix="FactopiaVoice-$version/" --output="$out" HEAD
echo "Built $out"
unzip -l "$out" | tail -n 1
