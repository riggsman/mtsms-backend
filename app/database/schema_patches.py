"""
Lightweight schema patches for columns added after initial deploy.
Runs on startup so dev DBs work before `alembic upgrade head`.
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)
_patched_engine_ids: set[int] = set()


def ensure_schema_patches(engine) -> None:
    """Run patches once per SQLAlchemy engine (shared + tenant DBs)."""
    key = id(engine)
    if key in _patched_engine_ids:
        return
    apply_schema_patches(engine)
    _patched_engine_ids.add(key)


def apply_schema_patches(engine) -> None:
    """Apply idempotent column/index patches on the default (tenant) database."""
    try:
        inspector = inspect(engine)
        if "school_fees" not in inspector.get_table_names():
            return

        columns = {c["name"] for c in inspector.get_columns("school_fees")}
        indexes = {idx["name"] for idx in inspector.get_indexes("school_fees")}

        with engine.begin() as conn:
            if "academic_year_id" not in columns:
                logger.info("Patching school_fees: adding academic_year_id column")
                conn.execute(
                    text("ALTER TABLE school_fees ADD COLUMN academic_year_id INTEGER NULL")
                )

            if "ix_school_fees_academic_year_id" not in indexes:
                dialect = engine.dialect.name
                logger.info("Patching school_fees: adding academic_year_id index")
                if dialect in ("mysql", "mariadb"):
                    try:
                        conn.execute(
                            text(
                                "CREATE INDEX ix_school_fees_academic_year_id "
                                "ON school_fees (academic_year_id)"
                            )
                        )
                    except OperationalError as sql_err:
                        orig = getattr(sql_err, "orig", None)
                        if getattr(orig, "args", None) and orig.args[0] == 1061:
                            logger.info(
                                "School_fees index already exists; ignoring duplicate key error"
                            )
                        else:
                            raise
                elif dialect == "sqlite":
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_school_fees_academic_year_id "
                            "ON school_fees (academic_year_id)"
                        )
                    )
    except Exception as exc:
        logger.warning("Schema patch skipped or failed: %s", exc)
