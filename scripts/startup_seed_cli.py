"""
CLI for managing the one-time startup seed marker.

Usage (from mtsms-backend folder):
  python scripts/startup_seed_cli.py status
  python scripts/startup_seed_cli.py clear
  python scripts/startup_seed_cli.py mark
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.conf.config import settings
from app.services.startup_seed import STARTUP_SEED_ONCE_KEY


def cmd_status(conn) -> int:
    rows = conn.execute(
        text("SELECT `value` FROM system_config WHERE `key` = :k LIMIT 1"),
        {"k": STARTUP_SEED_ONCE_KEY},
    ).fetchall()
    if not rows:
        print(f"{STARTUP_SEED_ONCE_KEY}=<missing> (seed WILL run on next app startup)")
        return 0
    value = rows[0][0]
    print(f"{STARTUP_SEED_ONCE_KEY}={value!s}")
    return 0


def cmd_clear(conn) -> int:
    res = conn.execute(
        text("DELETE FROM system_config WHERE `key` = :k"),
        {"k": STARTUP_SEED_ONCE_KEY},
    )
    print(f"Cleared marker ({res.rowcount} row(s) deleted). Seed WILL run on next app startup.")
    return 0


def cmd_mark(conn) -> int:
    # Use upsert-like behavior compatible with MySQL.
    conn.execute(
        text(
            """
            INSERT INTO system_config (`key`, `value`, `description`)
            VALUES (:k, 'true', 'Startup seed completed successfully at least once.')
            ON DUPLICATE KEY UPDATE
              `value` = 'true',
              `description` = 'Startup seed completed successfully at least once.'
            """
        ),
        {"k": STARTUP_SEED_ONCE_KEY},
    )
    print("Marker set to true. Seed will be skipped on next app startup.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the one-time startup seed marker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Show current marker value")
    sub.add_parser("clear", help="Delete marker so seed runs on next startup")
    sub.add_parser("mark", help="Set marker to true (skip seed on next startup)")
    args = parser.parse_args()

    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        if args.cmd == "status":
            return cmd_status(conn)
        if args.cmd == "clear":
            return cmd_clear(conn)
        if args.cmd == "mark":
            return cmd_mark(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

