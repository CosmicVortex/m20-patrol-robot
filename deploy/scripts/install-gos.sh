#!/usr/bin/env bash
# Install the read-only/simulated M20 service from a fixed local Git checkout.
# This script never connects to AOS/NOS and never enables robot control.
set -euo pipefail

REPO=''
REF=''
TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
APPLY=false

usage() {
  printf 'Usage: %s --repo PATH --ref COMMIT [--target-root PATH] [--apply]\n' "$0"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) [ "$#" -ge 2 ] || { printf 'ERROR: --repo requires a value\n' >&2; exit 2; }; REPO=$2; shift 2 ;;
    --ref) [ "$#" -ge 2 ] || { printf 'ERROR: --ref requires a value\n' >&2; exit 2; }; REF=$2; shift 2 ;;
    --target-root) [ "$#" -ge 2 ] || { printf 'ERROR: --target-root requires a value\n' >&2; exit 2; }; TARGET_ROOT=$2; shift 2 ;;
    --apply) APPLY=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] && [ -n "$REF" ] || { usage >&2; exit 2; }
[ -d "$REPO/.git" ] || { printf 'ERROR: --repo must be a Git checkout\n' >&2; exit 2; }
command -v git >/dev/null || { printf 'ERROR: git is required\n' >&2; exit 2; }
command -v python3 >/dev/null || { printf 'ERROR: python3 is required\n' >&2; exit 2; }
MANIFEST="$REPO/deploy/readonly-manifest.json"
validate_readonly_release() {
  local release="$1"
  [ -f "$MANIFEST" ] || { printf 'ERROR: manifest is missing\n' >&2; exit 2; }
  python3 - "$MANIFEST" "$release" <<'PY'
import json, pathlib, sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text())
r=pathlib.Path(sys.argv[2])
assert m["runtime_mode"] == "realtime_readonly"
assert m["read_only_mode"] is True and m["control_enabled"] is False
assert m["telemetry_rx_enabled"] is True and m["telemetry_tx_enabled"] is False
assert m["web_bind_host"] == "10.21.31.104"
assert m["targets"]["aos_host"] == "10.21.31.103"
assert m["ports"]["aos_tcp"] == 30001 and m["ports"]["web"] == 8080
unit=(r / "deploy/systemd/m20-patrol-readonly.service").read_text()
for item in ("M20_RUNTIME_MODE=realtime_readonly","M20_READ_ONLY_MODE=true","M20_CONTROL_ENABLED=false","M20_TELEMETRY_TX_ENABLED=false","M20_TARGET_HOST=10.21.31.103","host=\"10.21.31.104\"","port=8080","telemetry_receive_enabled=True"):
    assert item in unit, item
assert (r / "backend/app/dashboard_realtime.py").is_file()
PY
}
if [ "$APPLY" = true ]; then
  command -v systemctl >/dev/null || { printf 'ERROR: systemctl is required on the target GOS\n' >&2; exit 2; }
  systemctl --user show-environment >/dev/null 2>&1 || { printf 'ERROR: systemd user manager is unavailable\n' >&2; exit 2; }
  [ -z "$(git -C "$REPO" status --porcelain)" ] || { printf 'ERROR: repository worktree must be clean for --apply\n' >&2; exit 2; }
fi
if [[ ! "$REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
  printf 'ERROR: --ref must be a full 40-character hexadecimal commit SHA\n' >&2
  exit 2
fi
case "$TARGET_ROOT" in
  /*) ;;
  *) printf 'ERROR: --target-root must be absolute\n' >&2; exit 2 ;;
esac
case "$TARGET_ROOT" in
  *[!A-Za-z0-9._/-]*) printf 'ERROR: --target-root contains unsupported characters\n' >&2; exit 2 ;;
esac

if ! git -C "$REPO" cat-file -e "$REF^{commit}" 2>/dev/null; then
  printf 'ERROR: commit does not exist in repository: %s\n' "$REF" >&2
  exit 2
fi

COMMIT=$(git -C "$REPO" rev-parse "$REF^{commit}")
[ "$COMMIT" = "$REF" ] || { printf 'ERROR: --ref is not the exact commit SHA\n' >&2; exit 2; }
RELEASE="$TARGET_ROOT/releases/$COMMIT"
CURRENT="$TARGET_ROOT/current"

if [ "$APPLY" != true ]; then
  [ -f "$REPO/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: repository is missing systemd template\n' >&2; exit 1; }
  [ -f "$REPO/backend/app/dashboard_realtime.py" ] || { printf 'ERROR: repository is missing realtime dashboard\n' >&2; exit 1; }
  printf 'DRY_RUN=true\nCANDIDATE_COMMIT=%s\nCANDIDATE_RELEASE=%s\nNO_FILES_WRITTEN=true\nNO_SYSTEMD_CHANGE=true\n' "$COMMIT" "$RELEASE"
  exit 0
fi

mkdir -p "$TARGET_ROOT/releases"
if [ -e "$RELEASE" ]; then
  printf 'ERROR: release already exists: %s\n' "$RELEASE" >&2
  exit 2
fi

mkdir -p "$RELEASE"
git -C "$REPO" archive "$COMMIT" | tar -x -C "$RELEASE"
validate_readonly_release "$RELEASE"
OLD_CURRENT=''
OLD_UNIT=''
OLD_CURRENT_EXISTS=false
OLD_UNIT_EXISTS=false
UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"
if [ -L "$CURRENT" ]; then
  OLD_CURRENT=$(readlink "$CURRENT")
  OLD_CURRENT_EXISTS=true
fi
if [ -f "$UNIT_PATH" ]; then
  OLD_UNIT="$TARGET_ROOT/.previous-unit.$$"
  cp -p "$UNIT_PATH" "$OLD_UNIT"
  OLD_UNIT_EXISTS=true
fi
cleanup() {
  local status=$?
  rm -f "${UNIT_TMP:-}"
  if [ "$status" -ne 0 ]; then
    rm -rf "$RELEASE"
    if [ -n "$OLD_CURRENT" ]; then
      ln -s "$OLD_CURRENT" "$TARGET_ROOT/.current.rollback.$$"
      mv -Tf "$TARGET_ROOT/.current.rollback.$$" "$CURRENT"
    elif [ "$OLD_CURRENT_EXISTS" = false ]; then
      rm -f "$CURRENT"
    fi
    if [ -n "$OLD_UNIT" ] && [ -f "$OLD_UNIT" ]; then
      mkdir -p "$(dirname "$UNIT_PATH")"
      cp -p "$OLD_UNIT" "$UNIT_PATH"
      systemctl --user daemon-reload 2>/dev/null || true
      systemctl --user restart "$SERVICE_NAME" 2>/dev/null || true
    elif [ "$OLD_UNIT_EXISTS" = false ]; then
      rm -f "$UNIT_PATH"
      systemctl --user daemon-reload 2>/dev/null || true
    fi
  fi
  rm -f "$OLD_UNIT"
  exit "$status"
}
trap cleanup EXIT
[ -f "$RELEASE/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: release is missing systemd template\n' >&2; exit 1; }
[ -f "$RELEASE/backend/app/dashboard_realtime.py" ] || { printf 'ERROR: release is missing realtime dashboard\n' >&2; exit 1; }

# Reuse only the target's pre-approved system packages; do not download dependencies.
python3 -m venv --system-site-packages "$RELEASE/.venv"
VENV_VERSION="$($RELEASE/.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
[ "$VENV_VERSION" = 3.8 ] || { printf 'ERROR: release venv requires Python 3.8.x, got %s\n' "$VENV_VERSION" >&2; exit 1; }
if [ -x "$RELEASE/.venv/bin/pytest" ]; then
  PYTHONPATH="$RELEASE" "$RELEASE/.venv/bin/python" -m pytest -q
  TESTS='PASSED'
else
  printf 'ERROR: pytest is required to certify this release before installation\n' >&2
  exit 1
fi
PYTHONPATH="$RELEASE" "$RELEASE/.venv/bin/python" -m compileall -q "$RELEASE/backend"

mkdir -p "$HOME/.config/systemd/user"
UNIT_TMP="$HOME/.config/systemd/user/.${SERVICE_NAME}.tmp.$$"
sed "s#%h/m20-patrol-robot/current#$CURRENT#g; s#%h/m20-patrol-robot#$RELEASE#g" "$RELEASE/deploy/systemd/$SERVICE_NAME" > "$UNIT_TMP"
grep -Fq "ExecStart=$CURRENT/.venv/bin/python" "$UNIT_TMP" || { printf 'ERROR: generated unit path check failed\n' >&2; exit 1; }
chmod 600 "$UNIT_TMP"
if [ "$APPLY" != true ]; then
  printf 'DRY_RUN=true\nCANDIDATE_RELEASE=%s\nNO_SYSTEMD_CHANGE=true\n' "$RELEASE"
  exit 0
fi
mv -f "$UNIT_TMP" "$HOME/.config/systemd/user/$SERVICE_NAME"
NEW_LINK="$TARGET_ROOT/.current.$$"
ln -s "$RELEASE" "$NEW_LINK"
mv -Tf "$NEW_LINK" "$CURRENT"
systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME"
trap - EXIT
printf 'INSTALLED_COMMIT=%s\nSERVICE=%s\nTESTS=%s\nCONTROL_ENABLED=false\nWEB_BIND_HOST=10.21.31.104\nWEB_PORT=8080\n' "$COMMIT" "$SERVICE_NAME" "$TESTS"
