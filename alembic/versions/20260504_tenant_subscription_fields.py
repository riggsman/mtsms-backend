"""tenants: subscription plan and start date

Revision ID: 20260504_tenant_subscription
Revises: 20260503_tenant_suspension
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260504_tenant_subscription"
down_revision: Union[str, Sequence[str], None] = "20260503_tenant_suspension"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "tenants" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "subscription_plan" not in columns:
        op.add_column(
            "tenants",
            sa.Column("subscription_plan", sa.String(length=64), nullable=True),
        )
    if "subscription_started_at" not in columns:
        op.add_column(
            "tenants",
            sa.Column("subscription_started_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "tenants" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "subscription_started_at" in columns:
        op.drop_column("tenants", "subscription_started_at")
    if "subscription_plan" in columns:
        op.drop_column("tenants", "subscription_plan")
