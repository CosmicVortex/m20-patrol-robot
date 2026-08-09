#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "$0")/.." && pwd)/scripts/install-gos.sh"
grep -Fq '"$PYTHON38_BIN" -m venv --system-site-packages "$RELEASE/.venv"' "$SCRIPT_PATH"
grep -Fq 'do not download dependencies' "$SCRIPT_PATH"
! grep -Fq 'pkill -9 -f' "$(cd "$(dirname "$SCRIPT_PATH")" && pwd)/start.sh"
grep -Fq 'M20_RUNTIME_MODE=realtime_readonly' "$(cd "$(dirname "$SCRIPT_PATH")/../systemd" && pwd)/m20-patrol-readonly.service"
DEPLOY_PATH="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)/deploy-readonly.sh"
DRY_RUN_OUTPUT="$(bash "$DEPLOY_PATH" --dry-run)"
printf '%s\n' "$DRY_RUN_OUTPUT" | grep -Fq 'NO_FILES_WRITTEN=true'
grep -Fq '10.21.31.103' "$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)/deploy/readonly-manifest.json"
grep -Fq 'dashboard_realtime.py' "$SCRIPT_PATH" || grep -Fq 'backend.app.server' "$SCRIPT_PATH"
! grep -R -n '10\.21\.31\.101' "$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)/deploy/scripts" "$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)/deploy/systemd" --include='*.py' --include='*.sh' --include='*.service'
printf 'install-venv-policy=OK\n'