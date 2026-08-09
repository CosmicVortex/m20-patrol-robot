#!/usr/bin/env bash
# Create a fixed-source deployment archive from the current Git commit.
# Run from a clean checkout after commit; the archive is for GOS read-only deployment.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/reports/m20-patrol-robot-deploy.zip}"
cd "$ROOT"
[ -z "$(git status --porcelain)" ] || { echo 'BLOCKED: worktree must be clean before packaging' >&2; exit 2; }
COMMIT="$(git rev-parse HEAD)"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"
cleanup(){ rm -rf "$TMP"; }
trap cleanup EXIT
mkdir -p "$TMP/m20-patrol-robot"
git archive "$COMMIT" | tar -x -C "$TMP/m20-patrol-robot"
printf '{"commit":"%s","created_by":"package-deploy.sh"}\n' "$COMMIT" > "$TMP/m20-patrol-robot/deploy/release-provenance.json"
sha256sum "$TMP/m20-patrol-robot/deploy/readonly-manifest.json" > "$TMP/m20-patrol-robot/deploy/manifest.sha256"
(cd "$TMP" && zip -qr "$OUT" m20-patrol-robot)
sha256sum "$OUT"
printf 'PACKAGE=%s\nCOMMIT=%s\n' "$OUT" "$COMMIT"
