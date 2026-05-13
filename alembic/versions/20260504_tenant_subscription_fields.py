"""tenants: subscription plan and start date

Revision ID: 20260504_tenant_subscription
Revises: 20260503_tenant_suspension
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260504_tenant_subscription"
down_revision: Union[str, Sequence[str], None] = "20260503_tenant_suspension"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("subscription_plan", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("subscription_started_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "subscription_started_at")
    op.drop_column("tenants", "subscription_plan")
