"""Add global system semesters table.

Revision ID: 20260604_system_semesters
Revises: 20260603_verified_documents
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


revision = "20260604_system_semesters"
down_revision = "20260603_verified_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "system_semesters" in inspector.get_table_names():
        return

    op.create_table(
        "system_semesters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint("uq_system_semesters_name", "system_semesters", ["name"])
    op.create_unique_constraint("uq_system_semesters_code", "system_semesters", ["code"])

    table = sa.table(
        "system_semesters",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("code", sa.String),
        sa.column("display_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.utcnow()
    op.bulk_insert(
        table,
        [
            {"id": 1, "name": "First Semester", "code": "SEM1", "display_order": 1, "is_active": True, "created_at": now, "updated_at": None},
            {"id": 2, "name": "Second Semester", "code": "SEM2", "display_order": 2, "is_active": True, "created_at": now, "updated_at": None},
            {"id": 3, "name": "Summer", "code": "SUMMER", "display_order": 3, "is_active": True, "created_at": now, "updated_at": None},
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "system_semesters" not in inspector.get_table_names():
        return
    op.drop_constraint("uq_system_semesters_code", "system_semesters", type_="unique")
    op.drop_constraint("uq_system_semesters_name", "system_semesters", type_="unique")
    op.drop_table("system_semesters")

