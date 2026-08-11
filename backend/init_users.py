#!/usr/bin/env python3
"""M20 Pro 初始化脚本 — 预置 admin 账户并写入密码到安全位置。

用法:
    python3 backend/init_users.py [--db PATH] [--output PATH]

在 GOS 部署后首次启动前运行一次即可。
"""
import argparse
import hashlib
import os
import secrets
import sqlite3
import sys
from pathlib import Path

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc

PASSWORD = "m20_patrol_2026"
DB_DEFAULT = str(Path.home() / "m20-patrol-robot" / "var" / "m20_auth.db")
OUTPUT_DEFAULT = str(Path.home() / ".config" / "m20-patrol" / "passwords.env")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return "$".join(("pbkdf2_sha256", "240000", salt.hex(), digest.hex()))


def ensure_admin(db_path: str, output_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        )
    """)
    conn.commit()

    exists = conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone()
    if not exists:
        h = hash_password(PASSWORD)
        conn.execute(
            "INSERT INTO users(username, password_hash, role, created_at) VALUES(?,?,?,?)",
            ("admin", h, "admin", datetime.now(UTC).isoformat()),
        )
        conn.commit()
        print(f"[OK] 已创建 admin 账户，密码已写入 {output_path}")
    else:
        print("[OK] admin 账户已存在，无需重复创建")

    conn.close()

    # Write passwords.env
    with open(output_path, "w") as f:
        f.write(f"M20_ADMIN_PASSWORD={PASSWORD}\n")
    os.chmod(output_path, 0o600)
    print(f"[OK] 密码文件已写入 {output_path} (权限 600)")


def main() -> None:
    parser = argparse.ArgumentParser(description="M20 Pro 用户初始化")
    parser.add_argument("--db", default=DB_DEFAULT, help="SQLite 数据库路径")
    parser.add_argument("--output", default=OUTPUT_DEFAULT, help="密码输出文件路径")
    args = parser.parse_args()
    ensure_admin(args.db, args.output)


if __name__ == "__main__":
    main()
