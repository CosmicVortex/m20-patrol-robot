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
COMMIT="$REF"
RELEASE="$TARGET_ROOT/releases/$COMMIT"
[ -d "$RELEASE" ] || { printf 'ERROR: installed release not found: %s\n' "$RELEASE" >&2; exit 2; }
[ -x "$RELEASE/.venv/bin/python" ] || { printf 'ERROR: release Python is missing\n' >&2; exit 2; }
[ -f "$RELEASE/backend/app/dashboard.py" ] || { printf 'ERROR: release dashboard is missing\n' >&2; exit 2; }
[ -f "$RELEASE/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: release systemd template is missing\n' >&2; exit 2; }

# Save current state before any changes for transaction rollback
SAVED_UNIT="$TARGET_ROOT/.rollback.saved-unit.$$"
SAVED_CURRENT_LINK="$TARGET_ROOT/.rollback.current-link.$$"
cleanup() {
  local status=$?
  rm -f "$SAVED_UNIT" "$SAVED_CURRENT_LINK"
  if [ "$status" -ne 0 ]; then
    printf 'ERROR: Rollback failed, restoring from saved state\n' >&2
    # Attempt to restore saved unit file
    if [ -f "$SAVED_UNIT" ] && [ -f "$UNIT_PATH" ]; then
      cp -p "$SAVED_UNIT" "$UNIT_PATH"
      systemctl --user daemon-reload 2>/dev/null || true
    fi
  fi
  exit "$status"
}
trap cleanup EXIT

# Save current unit file before overwriting
if [ -f "$UNIT_PATH" ]; then
  cp -p "$UNIT_PATH" "$SAVED_UNIT"
fi

mkdir -p "$HOME/.config/systemd/user"
UNIT_TMP="$HOME/.config/systemd/user/.${SERVICE_NAME}.tmp.$$"
trap 'rm -f "$UNIT_TMP" "$SAVED_UNIT"' EXIT
sed "s#%h/m20-patrol-robot#$RELEASE#g" "$RELEASE/deploy/systemd/$SERVICE_NAME" > "$UNIT_TMP"
grep -Fq "ExecStart=$RELEASE/.venv/bin/python" "$UNIT_TMP" || { printf 'ERROR: generated unit path check failed\n' >&2; exit 1; }
chmod 600 "$UNIT_TMP"
mv -f "$UNIT_TMP" "$UNIT_PATH"
systemctl --user daemon-reload
systemctl --user restart "$SERVICE_NAME"
NEW_LINK="$TARGET_ROOT/.current.$$"
ln -s "$RELEASE" "$NEW_LINK"
mv -Tf "$NEW_LINK" "$TARGET_ROOT/current"
trap - EXIT
printf 'ROLLED_BACK_COMMIT=%s\nSERVICE=%s\nCONTROL_ENABLED=false\nBIND=127.0.0.1\n' "$COMMIT" "$SERVICE_NAME"
