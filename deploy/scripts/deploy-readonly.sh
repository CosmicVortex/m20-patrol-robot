#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT/deploy/readonly-manifest.json"
TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
GOS_HOST=''
AOS_HOST=''
NOS_HOST=''
AOS_TCP_PORT=''
AOS_UDP_PORT=''
RTSP_PORT=''
WEB_PORT=''
STALE_AFTER_SECONDS=''
PYTHON_BIN=''

say() { printf '%s\n' "$*"; }
fail() { say "BLOCKED:$*" >&2; exit 2; }

load_manifest_values() {
  [ -f "$MANIFEST" ] || fail 'MANIFEST_MISSING'
  IFS=$'\t' read -r GOS_HOST AOS_HOST NOS_HOST AOS_TCP_PORT AOS_UDP_PORT RTSP_PORT WEB_PORT STALE_AFTER_SECONDS < <(
    python3 - "$MANIFEST" <<'PY'
import json, sys
d=json.load(open(sys.argv[1]))
print("\t".join([
    d["targets"]["gos_host"], d["targets"]["aos_host"], d["targets"]["nos_host"],
    str(d["ports"]["aos_tcp"]), str(d["ports"]["aos_udp"]),
    str(d["ports"]["rtsp"]), str(d["ports"]["web"]),
    str(d["stale_after_seconds"]),
]))
PY
  )
}

check_manifest() {
  [ -f "$MANIFEST" ] || fail 'MANIFEST_MISSING'
  command -v python3 >/dev/null || fail 'PYTHON3_MISSING'
  python3 - "$MANIFEST" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p))
assert d["runtime_mode"] == "realtime_readonly"
assert d["read_only_mode"] is True
assert d["control_enabled"] is False
assert d["telemetry_rx_enabled"] is True
assert d["telemetry_tx_enabled"] is False
assert d["web_realtime_enabled"] is True
assert d["web_bind_host"] == "10.21.31.104"
assert d["stale_after_seconds"] == 3
assert d["targets"] == {"gos_host":"10.21.31.104","aos_host":"10.21.31.103","nos_host":"10.21.31.106"}
assert d["ports"] == {"aos_tcp":30001,"aos_udp":30000,"rtsp":8554,"web":8080}
assert d["credentials_included"] is False
PY
  if grep -R -n '10\.21\.31\.101' "$ROOT/deploy" "$ROOT/backend" --include='*.py' --include='*.sh' --include='*.service' >/dev/null; then fail 'DEPRECATED_ADDRESS_PRESENT'; fi
  if grep -R -n -E 'pkill|nohup' "$ROOT/deploy/scripts" --include='*.sh' --exclude='deploy-readonly.sh' >/dev/null; then
    fail 'UNSAFE_PROCESS_CONTROL_PRESENT'
  fi
}

check_clean_source() {
  if [ -d "$ROOT/.git" ] || [ -f "$ROOT/.git" ]; then
    [ -z "$(git -C "$ROOT" status --porcelain)" ] || fail 'WORKTREE_DIRTY_COMMIT_REQUIRED'
  else
    [ -f "$ROOT/deploy/release-provenance.json" ] || fail 'RELEASE_PROVENANCE_MISSING'
  fi
}

source_ref() {
  if [ -d "$ROOT/.git" ] || [ -f "$ROOT/.git" ]; then git -C "$ROOT" rev-parse HEAD; else
    python3 - "$ROOT/deploy/release-provenance.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["commit"])
PY
  fi
}

check_python() {
  PYTHON_BIN="$(command -v python3.8 || true)"
  [ -n "$PYTHON_BIN" ] || fail 'PY38_RUNTIME_CHECK_BLOCKED'
  "$PYTHON_BIN" -c 'import sys; assert sys.version_info[:3] == (3,8,10)' || fail 'PY38_RUNTIME_CHECK_BLOCKED'
  say 'PY38_RUNTIME_CHECK=PASS'
  "$PYTHON_BIN" -m compileall -q "$ROOT/backend" || fail 'COMPILE_FAILED'
  PYTHONPATH="$ROOT" "$PYTHON_BIN" - <<'PY' || fail 'PY38_IMPORT_CHECK_FAILED'
from backend.app.dashboard_realtime import DashboardConfig, RealTimeDashboard
from backend.app.robot.telemetry import ConnectionConfig
assert DashboardConfig().read_only_mode is True
assert ConnectionConfig(host="10.21.31.103").telemetry_tx_enabled is False
PY
  say 'PY38_AST_CHECK=PASS'
  say 'PY38_IMPORT_CHECK=PASS'
}

check_host() {
  say "GOS_HOST=$GOS_HOST AOS_HOST=$AOS_HOST NOS_HOST=$NOS_HOST"
  say "AOS_TCP_PORT=$AOS_TCP_PORT AOS_UDP_PORT=$AOS_UDP_PORT RTSP_PORT=$RTSP_PORT WEB_PORT=$WEB_PORT"
  say "USER=$(id -un) UID=$(id -u) ARCH=$(uname -m)"
  command -v systemctl >/dev/null || fail 'SYSTEMCTL_MISSING'
  systemctl --user show-environment >/dev/null 2>&1 || fail 'SYSTEMD_USER_UNAVAILABLE'
  [ "$(id -u)" != 0 ] || fail 'ROOT_USER_NOT_ALLOWED'
  command -v ip >/dev/null || fail 'IP_COMMAND_MISSING'
  ip -4 -o addr show | awk '{print $4}' | cut -d/ -f1 | grep -Fxq "$GOS_HOST" || fail 'GOS_IDENTITY_MISMATCH'
  df -Pk "$TARGET_ROOT" 2>/dev/null | tail -1 || true
}

preflight() {
  load_manifest_values
  check_manifest
  check_python
  check_host
  grep -Fq 'M20_RUNTIME_MODE=realtime_readonly' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_RUNTIME_MODE_MISMATCH'
  grep -Fq 'M20_TARGET_HOST=@AOS_HOST@' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_TARGET_TEMPLATE_MISSING'
  grep -iqF 'control_enabled=false' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_CONTROL_NOT_DISABLED'
  grep -Fq 'telemetry_tx_enabled=False' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_TX_NOT_DISABLED'
  grep -Fq 'backend.app.server' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_ENTRYPOINT_MODERN_SERVER_MISSING'
  ! grep -Fq 'dashboard_realtime' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_ENTRYPOINT_LEGACY_STILL_PRESENT'
  conflict_active="$(systemctl --user show -p ActiveState --value m20-patrol-realtime.service)" || fail 'CONFLICTING_SERVICE_STATE_UNKNOWN'
  conflict_enabled="$(systemctl --user show -p UnitFileState --value m20-patrol-realtime.service)" || fail 'CONFLICTING_SERVICE_ENABLEMENT_UNKNOWN'
  [ "$conflict_active" = inactive ] || fail "CONFLICTING_REALTIME_SERVICE_STATE=$conflict_active"
  [ "$conflict_enabled" = disabled ] || fail "CONFLICTING_REALTIME_SERVICE_ENABLEMENT=$conflict_enabled"
  say 'TARGET_IDENTITY_CONFIRMED=PASS'
  say 'TELEMETRY_TX_ENABLED=false'
  say 'CONTROL_ENABLED=false'
  say 'WEB_REALTIME_ENABLED=true'
  say 'PREFLIGHT=PASS'
}

render_unit_template() {
  sed -e "s#%h/m20-patrol-robot/current#$TARGET_ROOT/current#g" \
      -e "s#%h/m20-patrol-robot#$TARGET_ROOT/current#g" \
      -e "s#@GOS_HOST@#$GOS_HOST#g" -e "s#@AOS_HOST@#$AOS_HOST#g" \
      -e "s#@AOS_TCP_PORT@#$AOS_TCP_PORT#g" -e "s#@WEB_PORT@#$WEB_PORT#g" \
      -e "s#@STALE_AFTER_SECONDS@#$STALE_AFTER_SECONDS#g" \
      -- \
      "$ROOT/deploy/systemd/m20-patrol-readonly.service"
}

install() {
  preflight
  check_clean_source
  [ -x "$ROOT/deploy/scripts/install-gos.sh" ] || fail 'INSTALL_SCRIPT_NOT_EXECUTABLE'
  local ref
  ref="$(source_ref)"
  "$ROOT/deploy/scripts/install-gos.sh" --repo "$ROOT" --ref "$ref" --target-root "$TARGET_ROOT" --apply
  systemctl --user daemon-reload || fail 'SYSTEMD_RELOAD_FAILED'
}

start() {
  preflight
  systemctl --user start "$SERVICE_NAME"
  say 'SERVICE_START=REQUESTED'
}

status() {
  preflight
  load_manifest_values
  systemctl --user --no-pager is-active "$SERVICE_NAME" >/dev/null || fail 'SERVICE_NOT_ACTIVE'
  say 'SERVICE_ACTIVE=confirmed'
}

case "${1:---one-shot}" in
  --preflight) preflight ;;
  --dry-run) load_manifest_values; check_manifest; "$ROOT/deploy/scripts/install-gos.sh" --repo "$ROOT" --ref "$(source_ref)" --target-root "$TARGET_ROOT"; say 'NO_FILES_WRITTEN=true'; say 'NO_SYSTEMD_CHANGE=true'; say 'NO_NETWORK_SIDE_EFFECT=true' ;;
  --install) install ;;
  --start) start ;;
  --status) status ;;
  --rollback) [ "${2:-}" ] || fail 'ROLLBACK_REQUIRES_COMMIT_SHA'; "$ROOT/deploy/scripts/rollback-gos.sh" --ref "$2" --target-root "$TARGET_ROOT" ;;
  --render-unit) render_unit_template ;;
  --one-shot) install; start; status ;;
  *) fail "UNKNOWN_MODE=$1" ;;
esac
