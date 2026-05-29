"""tenants: suspension reason and timestamp

Revision ID: 20260503_tenant_suspension
Revises: 20260502_system_permissions
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260503_tenant_suspension"
down_revision: Union[str, Sequence[str], None] = "20260502_system_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "tenants" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "suspension_reason" not in columns:
        op.add_column("tenants", sa.Column("suspension_reason", sa.Text(), nullable=True))
    if "suspended_at" not in columns:
        op.add_column("tenants", sa.Column("suspended_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "tenants" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "suspended_at" in columns:
        op.drop_column("tenants", "suspended_at")
    if "suspension_reason" in columns:
        op.drop_column("tenants", "suspension_reason")
