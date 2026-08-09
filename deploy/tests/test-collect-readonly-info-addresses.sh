#!/usr/bin/env bash
# Regression tests for deploy/scripts/collect-readonly-info.sh address validation.
# The script must fail before any network probe for rejected inputs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$ROOT/deploy/scripts/collect-readonly-info.sh"

expect_rejected() {
  local address="$1"
  set +e
  AOS_HOST="$address" GOS_HOST="10.21.31.104" NOS_HOST="10.21.31.106" \
    bash "$SCRIPT" >/dev/null 2>&1
  local status=$?
  set -e
  if [ "$status" -ne 2 ]; then
    printf 'expected rejection for %s, got exit %s\n' "$address" "$status" >&2
    exit 1
  fi
}

for address in \
  '10.21.31.103.' \
  '010.021.031.103' \
  '10.21.31' \
  '10.21.31.256' \
  '0.0.0.0' \
  '0.0.0.1' \
  '0.255.255.255' \
  '255.255.255.255' \
  '224.0.0.1' \
  '127.0.0.1' \
  '127.1.2.3' \
  '169.254.1.1' \
  '192.168.1.0' \
  '192.168.1.255' \
  '10.21.31.0' \
  '10.21.31.255'; do
  expect_rejected "$address"
done

printf 'address-validation-regression=OK\n'
