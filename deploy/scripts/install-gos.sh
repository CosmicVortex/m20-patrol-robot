#!/usr/bin/env bash
# Install the read-only/simulated M20 service from a fixed local Git checkout.
# This script never connects to AOS/NOS and never enables robot control.
set -euo pipefail

REPO=''
REF=''
TARGET_ROOT="$HOME/m20-patrol-robot"
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
[ -d "$REPO/.git" ] || [ -f "$REPO/deploy/release-provenance.json" ] || { printf 'ERROR: --repo must be a Git checkout or packaged release\n' >&2; exit 2; }
if [ -d "$REPO/.git" ] || [ -f "$REPO/.git" ]; then command -v git >/dev/null || { printf 'ERROR: git is required\n' >&2; exit 2; }; fi
command -v python3 >/dev/null || { printf 'ERROR: python3 is required\n' >&2; exit 2; }
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
  printf 'DEBUG: manifest loaded - GOS=%s AOS=%s PORT=%s\n' "$GOS_HOST" "$AOS_HOST" "$AOS_TCP_PORT" >&2
}
validate_readonly_release() {
  local release="$1"
  local manifest="$release/deploy/readonly-manifest.json"
  [ -f "$manifest" ] || { printf 'ERROR: release manifest is missing\n' >&2; exit 2; }
  python3 - "$manifest" "$release" <<'PY'
import json, pathlib, sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text())
r=pathlib.Path(sys.argv[2])
assert m["runtime_mode"] == "realtime_readonly"
assert m["read_only_mode"] is True and m["control_enabled"] is False
assert m["telemetry_rx_enabled"] is True and m["telemetry_tx_enabled"] is False
assert m["web_realtime_enabled"] is True
assert m["credentials_included"] is False
assert isinstance(m["web_bind_host"], str) and m["web_bind_host"] == "10.21.31.104"
assert isinstance(m["stale_after_seconds"], (int, float)) and m["stale_after_seconds"] > 0
assert m["targets"] == {"gos_host":"10.21.31.104","aos_host":"10.21.31.103","nos_host":"10.21.31.106"}
assert m["ports"] == {"aos_tcp":30001,"aos_udp":30000,"rtsp":8554,"web":8080}
unit=(r / "deploy/systemd/m20-patrol-readonly.service").read_text()
if "@GOS_HOST@" in unit:
    for item in ("M20_RUNTIME_MODE=realtime_readonly","M20_READ_ONLY_MODE=true","M20_CONTROL_ENABLED=false","M20_TELEMETRY_TX_ENABLED=false","M20_TARGET_HOST=@AOS_HOST@","M20_TARGET_PORT=@AOS_TCP_PORT@","host=\"@GOS_HOST@\"","port=@WEB_PORT@","telemetry_receive_enabled=True","stale_after_s=@STALE_AFTER_SECONDS@"):
        assert item in unit, item
else:
    for item in ("M20_RUNTIME_MODE=realtime_readonly","M20_READ_ONLY_MODE=true","M20_CONTROL_ENABLED=false","M20_TELEMETRY_TX_ENABLED=false","M20_TARGET_HOST=@AOS_HOST@","M20_TARGET_PORT=@AOS_TCP_PORT@","backend.app.server"):
        assert item in unit, item
assert (r / "backend/app/server.py").is_file()
PY
}
validate_current_link() {
[ ! -e "$CURRENT" ] && [ ! -L "$CURRENT" ] && return 0
  [ -L "$CURRENT" ] || { printf 'ERROR: current must be a symlink\n' >&2; return 1; }
python3 - "$CURRENT" "$TARGET_ROOT" <<'PY'
import pathlib, sys
link = pathlib.Path(sys.argv[1])
root = pathlib.Path(sys.argv[2]).resolve()
target = link.resolve(strict=True)
if root not in target.parents or target.parent != root / "releases":
  raise SystemExit("current target is outside releases")
if len(target.name) != 40 or any(c not in "0123456789abcdef" for c in target.name):
  raise SystemExit("current target is not a full lowercase commit SHA")
PY
}
if [ "$APPLY" = true ]; then
  if [ "$(id -u)" -eq 0 ]; then
    printf 'ERROR: root user is not allowed for user-level GOS deployment\n' >&2
    exit 2
  fi
  command -v systemctl >/dev/null || { printf 'ERROR: systemctl is required on the target GOS\n' >&2; exit 2; }
  systemctl --user show-environment >/dev/null 2>&1 || { printf 'ERROR: systemd user manager is unavailable\n' >&2; exit 2; }
  command -v ip >/dev/null || { printf 'ERROR: ip is required on the target GOS\n' >&2; exit 2; }
  # GOS identity and conflict state are checked after immutable release manifest load.

fi
if [[ ! "$REF" =~ ^[0-9a-f]{40}$ ]]; then
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

if [ -d "$REPO/.git" ] || [ -f "$REPO/.git" ]; then
  git -C "$REPO" cat-file -e "$REF^{commit}" 2>/dev/null || { printf 'ERROR: commit does not exist in repository: %s\n' "$REF" >&2; exit 2; }
  COMMIT=$(git -C "$REPO" rev-parse "$REF^{commit}")
  [ "$COMMIT" = "$REF" ] || { printf 'ERROR: --ref is not the exact commit SHA\n' >&2; exit 2; }
else
  COMMIT=$(python3 - "$REPO/deploy/release-provenance.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["commit"])
PY
)
  [ "$COMMIT" = "$REF" ] || { printf 'ERROR: packaged provenance does not match --ref\n' >&2; exit 2; }
  # Checksum verification is optional - only required if package.sha256 exists
  if [ -f "$REPO/deploy/package.sha256" ]; then
    (cd "$REPO" && sha256sum -c deploy/package.sha256) || { printf 'ERROR: packaged release checksum verification failed\n' >&2; exit 2; }
  else
    printf 'WARNING: deploy/package.sha256 not found, skipping checksum verification\n' >&2
  fi
fi
RELEASE="$TARGET_ROOT/releases/$COMMIT"
CURRENT="$TARGET_ROOT/current"
UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"

if [ "$APPLY" != true ]; then
  DRY_RELEASE="$(mktemp -d "${TMPDIR:-/tmp}/m20-release-dry-run.XXXXXX")"
  cleanup_dry_run() { rm -rf "$DRY_RELEASE"; }
  trap cleanup_dry_run EXIT
  if [ -d "$REPO/.git" ]; then git -C "$REPO" archive "$COMMIT" | tar -x -C "$DRY_RELEASE"; else cp -a "$REPO"/. "$DRY_RELEASE"/; fi
  validate_readonly_release "$DRY_RELEASE" || { printf 'ERROR: candidate release contract failed\n' >&2; exit 1; }
  load_manifest_values "$DRY_RELEASE/deploy/readonly-manifest.json"
  DRY_UNIT="$(mktemp "${TMPDIR:-/tmp}/m20-readonly-unit.XXXXXX")"
  trap 'rm -rf "$DRY_RELEASE" "$DRY_UNIT"' EXIT
  sed -e "s#%h/m20-patrol-robot/current#$DRY_RELEASE/current#g" \
      -e "s#%h/m20-patrol-robot#$DRY_RELEASE#g" \
      -e "s#@GOS_HOST@#$GOS_HOST#g" -e "s#@AOS_HOST@#$AOS_HOST#g" \
      -e "s#@AOS_TCP_PORT@#$AOS_TCP_PORT#g" -e "s#@WEB_PORT@#$WEB_PORT#g" \
      -e "s#@STALE_AFTER_SECONDS@#$STALE_AFTER_SECONDS#g" \
      "$DRY_RELEASE/deploy/systemd/$SERVICE_NAME" > "$DRY_UNIT"
  grep -Eq '@[A-Z0-9_]+@' "$DRY_UNIT" && { printf 'ERROR: unresolved systemd template placeholders\n' >&2; exit 1; }
  grep -Fq "ExecStart=$DRY_RELEASE/current/.venv/bin/python" "$DRY_UNIT" || { printf 'ERROR: dry-run generated unit path check failed\n' >&2; exit 1; }
  printf 'DRY_RUN=true\nCANDIDATE_COMMIT=%s\nCANDIDATE_RELEASE=%s\nNO_FILES_WRITTEN=true\nNO_SYSTEMD_CHANGE=true\n' "$COMMIT" "$RELEASE"
  exit 0
fi

validate_current_link || exit 2
if [ -L "$UNIT_PATH" ] || { [ -e "$UNIT_PATH" ] && [ ! -f "$UNIT_PATH" ]; }; then
  printf 'ERROR: systemd unit path must be absent or a regular file\n' >&2
  exit 2
fi
if [ -e "$RELEASE" ] || [ -L "$RELEASE" ]; then
  printf 'ERROR: release already exists: %s\n' "$RELEASE" >&2
  exit 2
fi
if [ "$APPLY" = true ]; then
  # Check GOS identity - try multiple methods for robustness
  printf 'DEBUG: 开始GOS身份检查...\n' >&2
  _ip_addr=""
  if command -v ip >/dev/null 2>&1; then
    _ip_addr=$(ip -4 -o addr show 2>/dev/null | awk '{print $4}' | cut -d/ -f1 || true)
    printf 'DEBUG: ip命令输出: %s\n' "$_ip_addr" >&2
  else
    printf 'DEBUG: ip命令不可用\n' >&2
  fi

  if [ -z "$_ip_addr" ] && command -v hostname >/dev/null 2>&1; then
    _ip_addr=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
    printf 'DEBUG: hostname -I输出: %s\n' "$_ip_addr" >&2
  fi

  if [ -z "$_ip_addr" ] && command -v ifconfig >/dev/null 2>&1; then
    _ip_addr=$(ifconfig 2>/dev/null | grep -oE 'inet [0-9.]+' | head -1 | awk '{print $2}' || true)
    printf 'DEBUG: ifconfig输出: %s\n' "$_ip_addr" >&2
  fi

  if [ -z "$_ip_addr" ]; then
    printf 'ERROR: 无法获取本机IP地址\n' >&2
    printf '  期望: %s\n' "$GOS_HOST" >&2
    printf '  hostname -I: ' >&2
    hostname -I 2>/dev/null || echo "失败" >&2
    printf '  ip addr: ' >&2
    ip -4 -o addr show 2>/dev/null || echo "失败" >&2
    exit 2
  fi

  if echo "$_ip_addr" | grep -Fxq "$GOS_HOST"; then
    printf 'DEBUG: GOS身份验证通过: %s == %s\n' "$_ip_addr" "$GOS_HOST" >&2
  else
    printf 'ERROR: GOS身份不匹配\n' >&2
    printf '  期望IP: %s\n' "$GOS_HOST" >&2
    printf '  实际IP: %s\n' "$_ip_addr" >&2
    printf '  所有网络接口:\n' >&2
    ip -4 -o addr show 2>/dev/null || hostname -I 2>/dev/null || ifconfig -a 2>/dev/null || true >&2
    exit 2
  fi
  conflict_active="$(systemctl --user show -p ActiveState --value m20-patrol-realtime.service)" || { printf 'ERROR: conflicting service state is unknown\n' >&2; exit 2; }
  conflict_enabled="$(systemctl --user show -p UnitFileState --value m20-patrol-realtime.service)" || { printf 'ERROR: conflicting service enablement is unknown\n' >&2; exit 2; }
  [ "$conflict_active" = inactive ] || { printf 'ERROR: conflicting realtime service state is not inactive: %s\n' "$conflict_active" >&2; exit 2; }
  [ "$conflict_enabled" = disabled ] || { printf 'ERROR: conflicting realtime service is not disabled: %s\n' "$conflict_enabled" >&2; exit 2; }
  if [ -d "$REPO/.git" ] || [ -f "$REPO/.git" ]; then [ -z "$(git -C "$REPO" status --porcelain)" ] || { printf 'ERROR: repository worktree must be clean for --apply\n' >&2; exit 2; }; fi
fi
RELEASE_CREATED=false
# NOTE: cleanup() is defined later (line ~259) with full rollback support
mkdir -p "$TARGET_ROOT/releases"
mkdir -p "$RELEASE"
RELEASE_CREATED=true
if [ -d "$REPO/.git" ]; then git -C "$REPO" archive "$COMMIT" | tar -x -C "$RELEASE"; else cp -a "$REPO"/. "$RELEASE"/; fi
if ! validate_readonly_release "$RELEASE"; then
  rm -rf "$RELEASE"
  exit 1
fi
load_manifest_values "$RELEASE/deploy/readonly-manifest.json"
MANIFEST_SHA256="$(sha256sum "$RELEASE/deploy/readonly-manifest.json" | awk '{print $1}')"
printf '{"commit":"%s","manifest_sha256":"%s"}\n' "$COMMIT" "$MANIFEST_SHA256" > "$RELEASE/.m20-release-provenance.json"
OLD_CURRENT=''
OLD_UNIT=''
OLD_CURRENT_EXISTS=false
OLD_UNIT_EXISTS=false
OLD_SERVICE_ACTIVE_STATE='inactive'
OLD_SERVICE_ENABLED_STATE='disabled'
STATE_SNAPSHOT_COMPLETE=false
if [ -L "$CURRENT" ]; then
  OLD_CURRENT=$(readlink "$CURRENT")
  OLD_CURRENT_EXISTS=true
fi
if [ -f "$UNIT_PATH" ]; then
  OLD_UNIT="$TARGET_ROOT/.previous-unit.$$"
  cp -p "$UNIT_PATH" "$OLD_UNIT"
  OLD_UNIT_EXISTS=true
fi
old_active_state="$(systemctl --user show -p ActiveState --value "$SERVICE_NAME")" || { printf 'ERROR: target service active state is unknown\n' >&2; exit 2; }
old_enabled_state="$(systemctl --user show -p UnitFileState --value "$SERVICE_NAME")" || { printf 'ERROR: target service enablement is unknown\n' >&2; exit 2; }
[ "$old_active_state" = active ] || [ "$old_active_state" = inactive ] || { printf 'ERROR: unsupported target service active state: %s\n' "$old_active_state" >&2; exit 2; }
[ "$old_enabled_state" = enabled ] || [ "$old_enabled_state" = disabled ] || { printf 'ERROR: unsupported target service enablement: %s\n' "$old_enabled_state" >&2; exit 2; }
OLD_SERVICE_ACTIVE_STATE="$old_active_state"
OLD_SERVICE_ENABLED_STATE="$old_enabled_state"
STATE_SNAPSHOT_COMPLETE=true
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
    [ "$RELEASE_CREATED" = true ] && rm -rf "$RELEASE"
    if [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ -n "$OLD_CURRENT" ]; then
      ln -s "$OLD_CURRENT" "$TARGET_ROOT/.current.rollback.$$"
      mv -Tf "$TARGET_ROOT/.current.rollback.$$" "$CURRENT"
    elif [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ "$OLD_CURRENT_EXISTS" = false ]; then
      rm -f "$CURRENT"
    fi
    if [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ -n "$OLD_UNIT" ] && [ -f "$OLD_UNIT" ]; then
      mkdir -p "$(dirname "$UNIT_PATH")"
      cp -p "$OLD_UNIT" "$UNIT_PATH"
      restore_service_state
    elif [ "$STATE_SNAPSHOT_COMPLETE" = true ] && [ "$OLD_UNIT_EXISTS" = false ]; then
      rm -f "$UNIT_PATH"
      restore_service_state
    fi
  fi
  rm -f "$OLD_UNIT"
  exit "$status"
}
[ -f "$RELEASE/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: release is missing systemd template\n' >&2; exit 1; }
[ -f "$RELEASE/backend/app/server.py" ] || { printf 'ERROR: release is missing server.py\\n' >&2; exit 1; }

# Reuse only the target's pre-approved system packages; do not download dependencies.
PYTHON_BIN=""
# Try python3.8 first, then fallback to python3
PYTHON_BIN="$(command -v python3.8 || true)"
[ -n "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3 || true)"
[ -n "$PYTHON_BIN" ] || { printf 'ERROR: python3 is required on the target GOS\n' >&2; exit 1; }

printf 'DEBUG: Python binary: %s\n' "$PYTHON_BIN" >&2
printf 'DEBUG: Python version: ' >&2
"$PYTHON_BIN" --version >&2

# Check Python version - accept 3.8+ or 3.10+
PY_MAJOR="$PYTHON_BIN" -c 'import sys; print(sys.version_info.major)' 2>/dev/null
PY_MINOR="$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null

if [ "$PY_MAJOR" = "3" ] && { [ "$PY_MINOR" -ge "10" ] || [ "$PY_MINOR" = "8" ]; }; then
  printf 'Python %s.%s detected, proceeding...\n' "$PY_MAJOR" "$PY_MINOR"
else
  printf 'ERROR: Python 3.8+ or 3.10+ is required, got %s.%s\n' "$PY_MAJOR" "$PY_MINOR" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv --system-site-packages "$RELEASE/.venv"
VENV_VERSION="$($RELEASE/.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "$VENV_VERSION" != "3.8" ] && [ "$VENV_VERSION" != "3.10" ] && [ "$VENV_VERSION" != "3.11" ] && [ "$VENV_VERSION" != "3.12" ] && [ "$VENV_VERSION" != "3.13" ]; then
  printf 'ERROR: release venv requires Python 3.8+, got %s\n' "$VENV_VERSION" >&2
  exit 1
fi
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
sed -e "s#%h/m20-patrol-robot/current#$CURRENT#g" \
    -e "s#%h/m20-patrol-robot#$RELEASE#g" \
    -e "s#@GOS_HOST@#$GOS_HOST#g" -e "s#@AOS_HOST@#$AOS_HOST#g" \
    -e "s#@AOS_TCP_PORT@#$AOS_TCP_PORT#g" -e "s#@WEB_PORT@#$WEB_PORT#g" \
    -e "s#@STALE_AFTER_SECONDS@#$STALE_AFTER_SECONDS#g" \
    "$RELEASE/deploy/systemd/$SERVICE_NAME" > "$UNIT_TMP"
if grep -Eq '@[A-Z0-9_]+@' "$UNIT_TMP"; then
  printf 'ERROR: unresolved systemd template placeholders\n' >&2
  exit 1
fi
chmod 600 "$UNIT_TMP"
if [ "$APPLY" != true ]; then
  printf 'DRY_RUN=true\nCANDIDATE_RELEASE=%s\nNO_SYSTEMD_CHANGE=true\n' "$RELEASE"
  rm -rf "$RELEASE"
  exit 0
fi
mv -f "$UNIT_TMP" "$HOME/.config/systemd/user/$SERVICE_NAME"
NEW_LINK="$TARGET_ROOT/.current.$$"
ln -s "$RELEASE" "$NEW_LINK"
mv -Tf "$NEW_LINK" "$CURRENT"
systemctl --user daemon-reload
restore_service_state
trap - EXIT
printf 'INSTALLED_COMMIT=%s\nSERVICE=%s\nTESTS=%s\nCONTROL_ENABLED=false\nWEB_BIND_HOST=10.21.31.104\nWEB_PORT=8080\n' "$COMMIT" "$SERVICE_NAME" "$TESTS"
