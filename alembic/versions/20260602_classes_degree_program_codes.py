"""classes: degree_program_codes JSON for HI application levels

Revision ID: 20260602_class_degree_programs
Revises: 9bacb06b09f8
Create Date: 2026-06-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker


revision: str = "20260602_class_degree_programs"
down_revision: Union[str, Sequence[str], None] = "9bacb06b09f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "classes" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("classes")}
    if "degree_program_codes" not in cols:
        op.add_column(
            "classes",
            sa.Column("degree_program_codes", sa.JSON(), nullable=True),
        )

    # Backfill HI tenants with canonical application-level rows (idempotent by institution + code).
    Session = sessionmaker(bind=bind)
    session = Session()
    try:
        from app.helpers.hi_degree_program_classes import seed_hi_application_level_classes
        from app.models.tenant import Tenant

        for row in session.query(Tenant.id, Tenant.category).all():
            tid, cat = row[0], (row[1] or "").strip().upper()
            if cat == "HI":
                seed_hi_application_level_classes(session, int(tid))
    finally:
        session.close()


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "classes" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("classes")}
    if "degree_program_codes" in cols:
        op.drop_column("classes", "degree_program_codes")
