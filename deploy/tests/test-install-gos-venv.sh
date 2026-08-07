#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "$0")/.." && pwd)/scripts/install-gos.sh"
grep -Fq 'python3 -m venv --system-site-packages "$RELEASE/.venv"' "$SCRIPT_PATH"
grep -Fq 'do not download dependencies' "$SCRIPT_PATH"
printf 'install-venv-policy=OK\n'