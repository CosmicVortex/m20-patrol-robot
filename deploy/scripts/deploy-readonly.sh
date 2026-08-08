#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT/deploy/readonly-manifest.json"
TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
GOS_HOST='10.21.31.104'
AOS_HOST='10.21.31.103'
NOS_HOST='13.21.31.106'
AOS_TCP_PORT=30001
AOS_UDP_PORT=30000
RTSP_PORT=8554
WEB_PORT=8080

say() { printf '%s\n' "$*"; }
fail() { say "BLOCKED:$*" >&2; exit 2; }

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
assert d["targets"] == {"gos_host":"10.21.31.104","aos_host":"10.21.31.103","nos_host":"13.21.31.106"}
assert d["ports"] == {"aos_tcp":30001,"aos_udp":30000,"rtsp":8554,"web":8080}
assert d["credentials_included"] is False
PY
  grep -R -n '10\.21\.31\.101' "$ROOT/deploy" "$ROOT/backend" --include='*.py' --include='*.sh' --include='*.service' >/dev/null && fail 'DEPRECATED_ADDRESS_PRESENT'
  if grep -R -n -E 'pkill|nohup' "$ROOT/deploy/scripts" --include='*.sh' --exclude='deploy-readonly.sh' >/dev/null; then
    fail 'UNSAFE_PROCESS_CONTROL_PRESENT'
  fi
}

check_clean_source() {
  [ -z "$(git -C "$ROOT" status --porcelain)" ] || fail 'WORKTREE_DIRTY_COMMIT_REQUIRED'
}

check_python() {
  local version
  version="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  [ "$version" = 3.8 ] || fail 'PY38_RUNTIME_CHECK_BLOCKED'
  say 'PY38_RUNTIME_CHECK=PASS'
  python3 -m compileall -q "$ROOT/backend" || fail 'COMPILE_FAILED'
  python3 - <<'PY' || fail 'PY38_IMPORT_CHECK_FAILED'
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
  df -Pk "$TARGET_ROOT" 2>/dev/null | tail -1 || true
}

preflight() {
  check_manifest
  check_python
  grep -Fq 'M20_RUNTIME_MODE=realtime_readonly' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_RUNTIME_MODE_MISMATCH'
  grep -Fq 'M20_TARGET_HOST=10.21.31.103' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_TARGET_MISMATCH'
  grep -Fq 'host="10.21.31.104"' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_BIND_MISMATCH'
  grep -Fq 'port=8080' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_WEB_PORT_MISMATCH'
  grep -Fq 'control_enabled=False' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_CONTROL_NOT_DISABLED'
  grep -Fq 'telemetry_tx_enabled=False' "$ROOT/deploy/systemd/m20-patrol-readonly.service" || fail 'UNIT_TX_NOT_DISABLED'
  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user is-active --quiet m20-patrol-realtime.service && fail 'CONFLICTING_REALTIME_SERVICE_ACTIVE' || true
    systemctl --user is-enabled --quiet m20-patrol-realtime.service && fail 'CONFLICTING_REALTIME_SERVICE_ENABLED' || true
  fi
  check_host
  say 'TARGET_IDENTITY_CONFIRMED=PROJECT_OWNER_CONFIRMED_FIXED_FACT'
  say 'TELEMETRY_TX_ENABLED=false'
  say 'CONTROL_ENABLED=false'
  say 'WEB_REALTIME_ENABLED=true'
  say 'PREFLIGHT=PASS'
}

install() {
  preflight
  check_clean_source
  [ -x "$ROOT/deploy/scripts/install-gos.sh" ] || chmod +x "$ROOT/deploy/scripts/install-gos.sh"
  local ref
  ref="$(git -C "$ROOT" rev-parse HEAD)"
  "$ROOT/deploy/scripts/install-gos.sh" --repo "$ROOT" --ref "$ref" --target-root "$TARGET_ROOT" --apply
}

start() {
  systemctl --user start "$SERVICE_NAME"
  say 'SERVICE_START=REQUESTED'
}

status() {
  systemctl --user --no-pager is-active "$SERVICE_NAME" >/dev/null || fail 'SERVICE_NOT_ACTIVE'
  local payload
  curl -fsS "http://${GOS_HOST}:${WEB_PORT}/api/v1/health" >/dev/null || fail 'REALTIME_HEALTH_NOT_READY'
  payload="$(curl -fsS "http://${GOS_HOST}:${WEB_PORT}/api/v1/status/latest")" || fail 'STATUS_ENDPOINT_UNAVAILABLE'
  python3 - "$payload" <<'PY'
import json, sys
d=json.loads(sys.argv[1])
required=("source","connected","valid_frames","age_ms")
missing=[k for k in required if k not in d]
if missing: raise SystemExit("STATUS_FIELDS_MISSING="+','.join(missing))
if d.get("source") != "REAL" or d.get("connected") is not True or d.get("valid_frames", 0) <= 0 or d.get("age_ms") is None or d.get("age_ms") < 0 or d.get("age_ms") >= 3000:
  raise SystemExit("REALTIME_DATA_NOT_FRESH")
print(json.dumps(d, ensure_ascii=False))
PY
}

case "${1:---one-shot}" in
  --preflight) preflight ;;
  --dry-run) check_manifest; say 'DRY_RUN=true'; say 'NO_FILES_WRITTEN=true'; say 'NO_SYSTEMD_CHANGE=true' ;;
  --install) install ;;
  --start) start ;;
  --status) status ;;
  --rollback) [ "${2:-}" ] || fail 'ROLLBACK_REQUIRES_COMMIT_SHA'; "$ROOT/deploy/scripts/rollback-gos.sh" --ref "$2" --target-root "$TARGET_ROOT" ;;
  --one-shot) install; start; status ;;
  *) fail "UNKNOWN_MODE=$1" ;;
esac
