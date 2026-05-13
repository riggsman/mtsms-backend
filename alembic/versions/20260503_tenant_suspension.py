"""tenants: suspension reason and timestamp

Revision ID: 20260503_tenant_suspension
Revises: 20260502_system_permissions
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260503_tenant_suspension"
down_revision: Union[str, Sequence[str], None] = "20260502_system_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("suspension_reason", sa.Text(), nullable=True))
    op.add_column("tenants", sa.Column("suspended_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "suspended_at")
    op.drop_column("tenants", "suspension_reason")
