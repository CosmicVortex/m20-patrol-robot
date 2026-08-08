#!/usr/bin/env bash
# Roll back the user-level read-only service to a selected installed commit.
set -euo pipefail

TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
REF=''
UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"

usage() { printf 'Usage: %s --ref COMMIT [--target-root PATH]\n' "$0"; }
while [ "$#" -gt 0 ]; do
  case "$1" in
    --ref) [ "$#" -ge 2 ] || { printf 'ERROR: --ref requires a value\n' >&2; exit 2; }; REF=$2; shift 2 ;;
    --target-root) [ "$#" -ge 2 ] || { printf 'ERROR: --target-root requires a value\n' >&2; exit 2; }; TARGET_ROOT=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REF" ] || { usage >&2; exit 2; }
case "$TARGET_ROOT" in
  /*) ;;
  *) printf 'ERROR: --target-root must be absolute\n' >&2; exit 2 ;;
esac
case "$TARGET_ROOT" in
  *[!A-Za-z0-9._/-]*) printf 'ERROR: --target-root contains unsupported characters\n' >&2; exit 2 ;;
esac
if [[ ! "$REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
  printf 'ERROR: --ref must be a 40-character hexadecimal commit SHA\n' >&2
  exit 2
fi
COMMIT="$(printf '%s' "$REF" | tr '[:upper:]' '[:lower:]')"
RELEASE="$TARGET_ROOT/releases/$COMMIT"
[ -d "$RELEASE" ] || { printf 'ERROR: installed release not found: %s\n' "$RELEASE" >&2; exit 2; }
[ -x "$RELEASE/.venv/bin/python" ] || { printf 'ERROR: release Python is missing\n' >&2; exit 2; }
[ -f "$RELEASE/backend/app/dashboard_realtime.py" ] || { printf 'ERROR: release realtime dashboard is missing\n' >&2; exit 2; }
[ -f "$RELEASE/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: release systemd template is missing\n' >&2; exit 2; }
python3 - "$RELEASE/deploy/readonly-manifest.json" "$RELEASE" <<'PY'
import json, pathlib, sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text()); r=pathlib.Path(sys.argv[2])
assert m["runtime_mode"] == "realtime_readonly"
assert m["read_only_mode"] is True and m["control_enabled"] is False
assert m["telemetry_tx_enabled"] is False and m["web_bind_host"] == "10.21.31.104"
assert m["targets"]["aos_host"] == "10.21.31.103"
assert (r / "backend/app/dashboard_realtime.py").is_file()
PY
VENV_VERSION="$($RELEASE/.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
[ "$VENV_VERSION" = 3.8 ] || { printf 'ERROR: rollback release requires Python 3.8.x, got %s\n' "$VENV_VERSION" >&2; exit 2; }

# Save current state before any changes for transaction rollback
SAVED_UNIT="$TARGET_ROOT/.rollback.saved-unit.$$"
SAVED_CURRENT_LINK="$TARGET_ROOT/.rollback.current-link.$$"
OLD_UNIT_EXISTS=false
OLD_CURRENT_EXISTS=false
cleanup() {
  local status=$?
  rm -f "${UNIT_TMP:-}"
  if [ "$status" -ne 0 ]; then
    printf 'ERROR: Rollback failed, restoring from saved state\n' >&2
    # Attempt to restore saved unit file
    if [ -f "$SAVED_UNIT" ]; then
      mkdir -p "$(dirname "$UNIT_PATH")"
      cp -p "$SAVED_UNIT" "$UNIT_PATH"
      systemctl --user daemon-reload 2>/dev/null || true
    elif [ "$OLD_UNIT_EXISTS" = false ]; then
      rm -f "$UNIT_PATH"
      systemctl --user daemon-reload 2>/dev/null || true
    fi
    if [ -f "$SAVED_CURRENT_LINK" ]; then
      rm -f "$TARGET_ROOT/current"
      ln -s "$(cat "$SAVED_CURRENT_LINK")" "$TARGET_ROOT/current"
    elif [ "$OLD_CURRENT_EXISTS" = false ]; then
      rm -f "$TARGET_ROOT/current"
    fi
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user restart "$SERVICE_NAME" 2>/dev/null || true
  fi
  rm -f "$SAVED_UNIT" "$SAVED_CURRENT_LINK"
  exit "$status"
}
trap cleanup EXIT

# Save current unit file before overwriting
if [ -f "$UNIT_PATH" ]; then
  OLD_UNIT_EXISTS=true
  cp -p "$UNIT_PATH" "$SAVED_UNIT"
fi
if [ -L "$TARGET_ROOT/current" ]; then
  OLD_CURRENT_EXISTS=true
  readlink "$TARGET_ROOT/current" > "$SAVED_CURRENT_LINK"
fi

mkdir -p "$HOME/.config/systemd/user"
UNIT_TMP="$HOME/.config/systemd/user/.${SERVICE_NAME}.tmp.$$"
trap cleanup EXIT
sed "s#%h/m20-patrol-robot/current#$TARGET_ROOT/current#g; s#%h/m20-patrol-robot#$RELEASE#g" "$RELEASE/deploy/systemd/$SERVICE_NAME" > "$UNIT_TMP"
grep -Fq "ExecStart=$TARGET_ROOT/current/.venv/bin/python" "$UNIT_TMP" || { printf 'ERROR: generated unit path check failed\n' >&2; exit 1; }
chmod 600 "$UNIT_TMP"
mv -f "$UNIT_TMP" "$UNIT_PATH"
NEW_LINK="$TARGET_ROOT/.current.$$"
ln -s "$RELEASE" "$NEW_LINK"
mv -Tf "$NEW_LINK" "$TARGET_ROOT/current"
systemctl --user daemon-reload
systemctl --user restart "$SERVICE_NAME"
rm -f "$SAVED_UNIT" "$SAVED_CURRENT_LINK"
trap - EXIT
printf 'ROLLED_BACK_COMMIT=%s\nSERVICE=%s\nCONTROL_ENABLED=false\nWEB_BIND_HOST=10.21.31.104\nWEB_PORT=8080\n' "$COMMIT" "$SERVICE_NAME"
