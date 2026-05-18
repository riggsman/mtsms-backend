"""
Repair alembic_version when revision IDs were truncated (VARCHAR(32)) causing overlap errors.

Run from mtsms-backend:
  python scripts/fix_alembic_version_overlap.py
Then:
  alembic upgrade head
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

from app.conf.config import settings

# Truncated at 32 chars when full id was 20260524_school_fees_academic_year
LEGACY_TRUNCATED_20260524 = "20260524_school_fees_academic_ye"
CANONICAL_20260524 = "20260524_school_fees_ay"
CANONICAL_20260525 = "20260525_academic_calendar"
CANONICAL_HEAD = "20260526_cal_date_range"


def main() -> None:
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE alembic_version "
                "MODIFY version_num VARCHAR(128) NOT NULL"
            )
        )
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        versions = [r[0] for r in rows]
        print("Before:", versions)

        conn.execute(
            text("DELETE FROM alembic_version WHERE version_num = :v"),
            {"v": LEGACY_TRUNCATED_20260524},
        )
        conn.execute(
            text("DELETE FROM alembic_version WHERE version_num = :v"),
            {"v": "20260524_school_fees_academic_year"},
        )

        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        versions = [r[0] for r in rows]

        if not versions:
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": CANONICAL_20260525},
            )
            print("Inserted default version:", CANONICAL_20260525)
        elif len(versions) > 1:
            conn.execute(text("DELETE FROM alembic_version"))
            keep = CANONICAL_20260525
            if CANONICAL_HEAD in versions:
                keep = CANONICAL_HEAD
            elif CANONICAL_20260525 in versions:
                keep = CANONICAL_20260525
            else:
                keep = max(versions)
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": keep},
            )
            print("Collapsed multiple rows to:", keep)
        elif versions[0] == LEGACY_TRUNCATED_20260524:
            conn.execute(text("DELETE FROM alembic_version"))
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": CANONICAL_20260524},
            )
            print("Replaced truncated revision with:", CANONICAL_20260524)

        after = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        print("After:", [r[0] for r in after])
    print("Done. Run: alembic upgrade head")


if __name__ == "__main__":
    main()
