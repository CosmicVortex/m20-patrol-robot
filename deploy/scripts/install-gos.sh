#!/usr/bin/env bash
# Install the read-only/simulated M20 service from a fixed local Git checkout.
# This script never connects to AOS/NOS and never enables robot control.
set -euo pipefail

REPO=''
REF=''
TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'

usage() {
  printf 'Usage: %s --repo PATH --ref COMMIT [--target-root PATH]\n' "$0"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) [ "$#" -ge 2 ] || { printf 'ERROR: --repo requires a value\n' >&2; exit 2; }; REPO=$2; shift 2 ;;
    --ref) [ "$#" -ge 2 ] || { printf 'ERROR: --ref requires a value\n' >&2; exit 2; }; REF=$2; shift 2 ;;
    --target-root) [ "$#" -ge 2 ] || { printf 'ERROR: --target-root requires a value\n' >&2; exit 2; }; TARGET_ROOT=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "$REPO" ] && [ -n "$REF" ] || { usage >&2; exit 2; }
[ -d "$REPO/.git" ] || { printf 'ERROR: --repo must be a Git checkout\n' >&2; exit 2; }
command -v git >/dev/null || { printf 'ERROR: git is required\n' >&2; exit 2; }
command -v python3 >/dev/null || { printf 'ERROR: python3 is required\n' >&2; exit 2; }
command -v systemctl >/dev/null || { printf 'ERROR: systemctl is required on the target GOS\n' >&2; exit 2; }
systemctl --user show-environment >/dev/null 2>&1 || { printf 'ERROR: systemd user manager is unavailable\n' >&2; exit 2; }
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
mkdir -p "$TARGET_ROOT/releases"
if [ -e "$RELEASE" ]; then
  printf 'ERROR: release already exists: %s\n' "$RELEASE" >&2
  exit 2
fi

mkdir -p "$RELEASE"
git -C "$REPO" archive "$COMMIT" | tar -x -C "$RELEASE"
OLD_CURRENT=''
OLD_UNIT=''
UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"
if [ -L "$CURRENT" ]; then
  OLD_CURRENT=$(readlink "$CURRENT")
fi
if [ -f "$UNIT_PATH" ]; then
  OLD_UNIT="$TARGET_ROOT/.previous-unit.$$"
  cp -p "$UNIT_PATH" "$OLD_UNIT"
fi
cleanup() {
  local status=$?
  rm -f "${UNIT_TMP:-}"
  if [ "$status" -ne 0 ]; then
    rm -rf "$RELEASE"
    if [ -n "$OLD_CURRENT" ]; then
      ln -s "$OLD_CURRENT" "$TARGET_ROOT/.current.rollback.$$"
      mv -Tf "$TARGET_ROOT/.current.rollback.$$" "$CURRENT"
    fi
    if [ -n "$OLD_UNIT" ] && [ -f "$OLD_UNIT" ]; then
      mkdir -p "$(dirname "$UNIT_PATH")"
      cp -p "$OLD_UNIT" "$UNIT_PATH"
    fi
  fi
  rm -f "$OLD_UNIT"
  exit "$status"
}
trap cleanup EXIT
[ -f "$RELEASE/deploy/systemd/$SERVICE_NAME" ] || { printf 'ERROR: release is missing systemd template\n' >&2; exit 1; }
[ -f "$RELEASE/backend/app/dashboard.py" ] || { printf 'ERROR: release is missing dashboard\n' >&2; exit 1; }

# Reuse only the target's pre-approved system packages; do not download dependencies.
python3 -m venv --system-site-packages "$RELEASE/.venv"
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
sed "s#%h/m20-patrol-robot#$RELEASE#g" "$RELEASE/deploy/systemd/$SERVICE_NAME" > "$UNIT_TMP"
grep -Fq "ExecStart=$RELEASE/.venv/bin/python" "$UNIT_TMP" || { printf 'ERROR: generated unit path check failed\n' >&2; exit 1; }
chmod 600 "$UNIT_TMP"
mv -f "$UNIT_TMP" "$HOME/.config/systemd/user/$SERVICE_NAME"
systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME"
NEW_LINK="$TARGET_ROOT/.current.$$"
ln -s "$RELEASE" "$NEW_LINK"
mv -Tf "$NEW_LINK" "$CURRENT"
trap - EXIT
printf 'INSTALLED_COMMIT=%s\nSERVICE=%s\nTESTS=%s\nCONTROL_ENABLED=false\nBIND=127.0.0.1\n' "$COMMIT" "$SERVICE_NAME" "$TESTS"
