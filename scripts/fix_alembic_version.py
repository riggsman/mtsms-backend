"""Fix duplicate/typo rows in alembic_version then upgrade to head."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.conf.config import settings

BAD_REVISION = "20260509_course_performance_date"  # typo (missing trailing 's')

engine = create_engine(settings.DATABASE_URL)
with engine.begin() as conn:
    rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    print("Before:", rows)
    deleted = conn.execute(
        text("DELETE FROM alembic_version WHERE version_num = :rev"),
        {"rev": BAD_REVISION},
    )
    print(f"Deleted typo row ({deleted.rowcount} row(s))")
    rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    print("After:", rows)
