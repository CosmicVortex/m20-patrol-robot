#!/usr/bin/env bash
# Roll back the user-level read-only service to a selected installed commit.
set -euo pipefail

TARGET_ROOT="$HOME/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
REF=''
UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"
GOS_HOST=''
AOS_HOST=''
AOS_TCP_PORT=''
WEB_PORT=''
STALE_AFTER_SECONDS=''
load_manifest_values() {
  local manifest="$1"
  IFS=$'\t' read -r GOS_HOST AOS_HOST AOS_TCP_PORT WEB_PORT STALE_AFTER_SECONDS < <(
    python3 - "$manifest" <<'PY'
import json, sys
d=json.load(open(sys.argv[1]))
print("\t".join([d["targets"]["gos_host"], d["targets"]["aos_host"], str(d["ports"]["aos_tcp"]), str(d["ports"]["web"]), str(d["stale_after_seconds"])]))
PY
  )
}

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
if [ "$(id -u)" -eq 0 ]; then
  printf 'ERROR: root user is not allowed for user-level GOS rollback\n' >&2
  exit 2
fi
command -v systemctl >/dev/null || { printf 'ERROR: systemctl is required on the target GOS\n' >&2; exit 2; }
systemctl --user show-environment >/dev/null 2>&1 || { printf 'ERROR: systemd user manager is unavailable\n' >&2; exit 2; }
command -v ip >/dev/null || { printf 'ERROR: ip is required on the target GOS\n' >&2; exit 2; }
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
RELEASE_REAL="$(readlink -f "$RELEASE")"
ROOT_REAL="$(readlink -f "$TARGET_ROOT/releases")"
[ "$RELEASE_REAL" = "$ROOT_REAL/$COMMIT" ] || { printf 'ERROR: release path escapes releases root\n' >&2; exit 2; }
[ "$(basename "$RELEASE_REAL")" = "$COMMIT" ] || { printf 'ERROR: release identity mismatch\n' >&2; exit 2; }
load_manifest_values "$RELEASE/deploy/readonly-manifest.json"
[ -f "$RELEASE/.m20-release-provenance.json" ] || { printf 'ERROR: release provenance is missing\n' >&2; exit 2; }
python3 - "$RELEASE/.m20-release-provenance.json" "$RELEASE/deploy/readonly-manifest.json" "$COMMIT" <<'PY'
import hashlib, json, pathlib, sys
p=json.loads(pathlib.Path(sys.argv[1]).read_text())
if p.get("commit") != sys.argv[3]: raise SystemExit("release provenance commit mismatch")
digest=hashlib.sha256(pathlib.Path(sys.argv[2]).read_bytes()).hexdigest()
if p.get("manifest_sha256") != digest: raise SystemExit("release provenance manifest mismatch")
PY
[ "$GOS_HOST" = "10.21.31.104" ] || { printf 'ERROR: release GOS target is not approved\n' >&2; exit 2; }
ip -4 -o addr show | awk '{print $4}' | cut -d/ -f1 | grep -Fxq "$GOS_HOST" || { printf 'ERROR: GOS identity mismatch\n' >&2; exit 2; }
conflict_active="$(systemctl --user show -p ActiveState --value m20-patrol-realtime.service)" || { printf 'ERROR: conflicting service state is unknown\n' >&2; exit 2; }
conflict_enabled="$(systemctl --user show -p UnitFileState --value m20-patrol-realtime.service)" || { printf 'ERROR: conflicting service enablement is unknown\n' >&2; exit 2; }
[ "$conflict_active" = inactive ] || { printf 'ERROR: conflicting realtime service state is not inactive: %s\n' "$conflict_active" >&2; exit 2; }
[ "$conflict_enabled" = disabled ] || { printf 'ERROR: conflicting realtime service is not disabled: %s\n' "$conflict_enabled" >&2; exit 2; }
[ ! -e "$TARGET_ROOT/current" ] && [ ! -L "$TARGET_ROOT/current" ] || [ -L "$TARGET_ROOT/current" ] || { printf 'ERROR: current must be a symlink\n' >&2; exit 2; }
if [ -L "$TARGET_ROOT/current" ]; then
  python3 - "$TARGET_ROOT/current" "$TARGET_ROOT" <<'PY'
import pathlib, sys
target = pathlib.Path(sys.argv[1]).resolve(strict=True)
root = pathlib.Path(sys.argv[2]).resolve()
if target.parent != root / "releases" or len(target.name) != 40 or any(c not in "0123456789abcdef" for c in target.name):
    raise SystemExit("current target is outside releases or invalid")
PY
fi
if [ -L "$UNIT_PATH" ] || { [ -e "$UNIT_PATH" ] && [ ! -f "$UNIT_PATH" ]; }; then
  printf 'ERROR: systemd unit path must be absent or a regular file\n' >&2
  exit 2
fi
[ -x "$RELEASE/.venv/bin/python" ] || { printf 'ERROR: release Python is missing\n' >&2; exit 2; }
[ -f "$RELEASE/backend/app/server.py" ] || { printf 'ERROR: release is missing server.py\\n' >&2; exit 2; }
[ -f "$RELEASE/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: release systemd template is missing\n' >&2; exit 2; }
python3 - "$RELEASE/deploy/readonly-manifest.json" "$RELEASE" <<'PY'
import json, pathlib, sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text()); r=pathlib.Path(sys.argv[2])
assert m["runtime_mode"] == "realtime_readonly"
assert m["read_only_mode"] is True and m["control_enabled"] is False
assert m["telemetry_rx_enabled"] is True and m["telemetry_tx_enabled"] is False
assert m["web_realtime_enabled"] is True and m["web_bind_host"] == "10.21.31.104"
assert m["stale_after_seconds"] == 3
assert m["targets"] == {"gos_host":"10.21.31.104","aos_host":"10.21.31.103","nos_host":"10.21.31.106"}
assert m["ports"] == {"aos_tcp":30001,"aos_udp":30000,"rtsp":8554,"web":8080}
assert m["credentials_included"] is False
unit=(r / "deploy/systemd/m20-patrol-readonly.service").read_text()
for item in ("M20_RUNTIME_MODE=realtime_readonly","M20_READ_ONLY_MODE=true","M20_CONTROL_ENABLED=false","M20_TELEMETRY_TX_ENABLED=false","M20_TARGET_HOST=@AOS_HOST@","M20_TARGET_PORT=@AOS_TCP_PORT@","backend.app.server"):
    assert item in unit, item
assert (r / "backend/app/server.py").is_file()
PY
VENV_VERSION="$($RELEASE/.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
# Accept Python 3.8+ or 3.10+
if [[ "$VENV_VERSION" =~ ^3\.(8|1[0-9])$ ]]; then
    printf 'Rollback release Python version: %s (OK)\n' "$VENV_VERSION"
else
    printf 'ERROR: rollback release requires Python 3.8+ or 3.10+, got %s\n' "$VENV_VERSION" >&2
    exit 2
fi

# Save current state before any changes for transaction rollback
SAVED_UNIT="$TARGET_ROOT/.rollback.saved-unit.$$"
SAVED_CURRENT_LINK="$TARGET_ROOT/.rollback.current-link.$$"
OLD_UNIT_EXISTS=false
OLD_CURRENT_EXISTS=false
OLD_SERVICE_ACTIVE=false
OLD_SERVICE_ENABLED=false
STATE_SNAPSHOT_COMPLETE=false
old_active_state="$(systemctl --user show -p ActiveState --value "$SERVICE_NAME")" || { printf 'ERROR: target service active state is unknown\n' >&2; exit 2; }
old_enabled_state="$(systemctl --user show -p UnitFileState --value "$SERVICE_NAME")" || { printf 'ERROR: target service enablement is unknown\n' >&2; exit 2; }
[ "$old_active_state" = active ] || [ "$old_active_state" = inactive ] || { printf 'ERROR: unsupported target service active state: %s\n' "$old_active_state" >&2; exit 2; }
[ "$old_enabled_state" = enabled ] || [ "$old_enabled_state" = disabled ] || { printf 'ERROR: unsupported target service enablement: %s\n' "$old_enabled_state" >&2; exit 2; }
OLD_SERVICE_ACTIVE_STATE="$old_active_state"
OLD_SERVICE_ENABLED_STATE="$old_enabled_state"
restore_service_state() {
  systemctl --user daemon-reload
  if [ "$OLD_SERVICE_ACTIVE_STATE" = active ]; then
    systemctl --user restart "$SERVICE_NAME"
  else
    systemctl --user stop "$SERVICE_NAME"
  fi
  if [ "$OLD_SERVICE_ENABLED_STATE" = enabled ]; then
    systemctl --user enable "$SERVICE_NAME"
  else
    systemctl --user disable "$SERVICE_NAME"
  fi
}
cleanup() {
  local status=$?
  rm -f "${UNIT_TMP:-}"
  if [ "$status" -ne 0 ]; then
    printf 'ERROR: Rollback failed, restoring from saved state\n' >&2
    # Attempt to restore saved unit file
    if [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ -f "$SAVED_UNIT" ]; then
      mkdir -p "$(dirname "$UNIT_PATH")"
      cp -p "$SAVED_UNIT" "$UNIT_PATH"
      systemctl --user daemon-reload
    elif [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ "$OLD_UNIT_EXISTS" = false ]; then
      rm -f "$UNIT_PATH"
      systemctl --user daemon-reload
    fi
    if [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ -f "$SAVED_CURRENT_LINK" ]; then
      rm -f "$TARGET_ROOT/current"
      ln -s "$(cat "$SAVED_CURRENT_LINK")" "$TARGET_ROOT/current"
    elif [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ "$OLD_CURRENT_EXISTS" = false ]; then
      rm -f "$TARGET_ROOT/current"
    fi
    if [ "$STATE_SNAPSHOT_COMPLETE" = true ]; then restore_service_state; fi
  fi
  rm -f "$SAVED_UNIT" "$SAVED_CURRENT_LINK"
  exit "$status"
}
trap cleanup EXIT

# Save current unit file before overwriting
if [ -f "$UNIT_PATH" ]; then
  OLD_UNIT_EXISTS=true
  cp -p "$UNIT_PATH" "$SAVED_UNIT" || exit 1
fi
if [ -L "$TARGET_ROOT/current" ]; then
  OLD_CURRENT_EXISTS=true
  readlink "$TARGET_ROOT/current" > "$SAVED_CURRENT_LINK" || exit 1
fi
STATE_SNAPSHOT_COMPLETE=true
mkdir -p "$HOME/.config/systemd/user"
UNIT_TMP="$HOME/.config/systemd/user/.${SERVICE_NAME}.tmp.$$"
trap cleanup EXIT
sed -e "s#%h/m20-patrol-robot/current#$TARGET_ROOT/current#g" \
    -e "s#%h/m20-patrol-robot#$RELEASE#g" \
    -e "s#@GOS_HOST@#$GOS_HOST#g" -e "s#@AOS_HOST@#$AOS_HOST#g" \
    -e "s#@AOS_TCP_PORT@#$AOS_TCP_PORT#g" -e "s#@WEB_PORT@#$WEB_PORT#g" \
    -e "s#@STALE_AFTER_SECONDS@#$STALE_AFTER_SECONDS#g" \
    "$RELEASE/deploy/systemd/$SERVICE_NAME" > "$UNIT_TMP"
if grep -Eq '@[A-Z0-9_]+@' "$UNIT_TMP"; then
  printf 'ERROR: unresolved systemd template placeholders\n' >&2
  exit 1
fi
grep -Fq "ExecStart=$TARGET_ROOT/current/.venv/bin/python" "$UNIT_TMP" || { printf 'ERROR: generated unit path check failed\n' >&2; exit 1; }
chmod 600 "$UNIT_TMP"
mv -f "$UNIT_TMP" "$UNIT_PATH"
NEW_LINK="$TARGET_ROOT/.current.$$"
ln -s "$RELEASE" "$NEW_LINK"
mv -Tf "$NEW_LINK" "$TARGET_ROOT/current"
systemctl --user daemon-reload
restore_service_state
rm -f "$SAVED_UNIT" "$SAVED_CURRENT_LINK"
trap - EXIT
printf 'ROLLED_BACK_COMMIT=%s\nSERVICE=%s\nCONTROL_ENABLED=false\nWEB_BIND_HOST=%s\nWEB_PORT=%s\n' "$COMMIT" "$SERVICE_NAME" "$GOS_HOST" "$WEB_PORT"
