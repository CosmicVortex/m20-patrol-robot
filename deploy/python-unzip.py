#!/usr/bin/env python3
"""Offline ZIP extraction fallback for GOS hosts without unzip."""
import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 python-unzip.py PACKAGE.zip")
    archive = Path(sys.argv[1]).resolve()
    with zipfile.ZipFile(archive) as zf:
        root = archive.parent.resolve()
        top_levels = {Path(member.filename).parts[0] for member in zf.infolist() if Path(member.filename).parts}
        for top_level in top_levels:
            if (root / top_level).exists() or (root / top_level).is_symlink():
                raise SystemExit(f"refusing to overwrite existing path: {top_level}")
        for member in zf.infolist():
            target = (root / member.filename).resolve()
            if root != target and root not in target.parents:
                raise SystemExit(f"unsafe archive path: {member.filename}")
        zf.extractall(root)
        for member in zf.infolist():
            target = (root / member.filename).resolve()
            mode = (member.external_attr >> 16) & 0o777
            if target.is_file() and mode:
                target.chmod(mode)



if __name__ == "__main__":
    main()
