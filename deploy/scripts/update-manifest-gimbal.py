#!/usr/bin/env python3
"""Update read-only manifest with gimbal configuration."""

import json
import sys
from pathlib import Path

MANIFEST_PATH = Path("deploy/readonly-manifest.json")

# Load existing manifest
with open(MANIFEST_PATH) as f:
    manifest = json.load(f)

# Add gimbal configuration
if "gimbal_host" not in manifest.get("targets", {}):
    manifest.setdefault("targets", {})["gimbal_host"] = "192.168.1.108"
    manifest.setdefault("targets", {})["gimbal_username"] = "admin"
    manifest.setdefault("targets", {})["gimbal_password"] = "123456"

# Save back
with open(MANIFEST_PATH, "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"[OK] Updated {MANIFEST_PATH}")
print(f"  gimbal_host: {manifest['targets']['gimbal_host']}")
print(f"  gimbal_username: {manifest['targets']['gimbal_username']}")
print(f"  gimbal_password: {'*' * len(manifest['targets']['gimbal_password'])}")
