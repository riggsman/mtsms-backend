"""Add current_semester_id to tenant_settings.

Revision ID: 20260604_tenant_current_semester
Revises: 20260604_system_semesters
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_tenant_current_semester"
down_revision = "20260604_system_semesters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_settings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("tenant_settings")}
    if "current_semester_id" in columns:
        return
    op.add_column("tenant_settings", sa.Column("current_semester_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tenant_settings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("tenant_settings")}
    if "current_semester_id" not in columns:
        return
    op.drop_column("tenant_settings", "current_semester_id")

