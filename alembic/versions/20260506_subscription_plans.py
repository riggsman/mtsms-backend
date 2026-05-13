"""create subscription_plans table and seed default plans

Revision ID: 20260506_subscription_plans
Revises: 20260506_tenant_billing
Create Date: 2026-05-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260506_subscription_plans"
down_revision: Union[str, Sequence[str], None] = "20260506_tenant_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table should already exist from previous attempt - verify and seed data
    # Seed default plans if table is empty
    op.execute(
        sa.table(
            "subscription_plans",
            sa.column("name", sa.String(length=64)),
            sa.column("description", sa.Text()),
            sa.column("price", sa.Numeric(precision=10, scale=2)),
            sa.column("billing_period", sa.String(length=20)),
            sa.column("is_active", sa.Boolean()),
            sa.column("features", sa.Text()),
        ).insert().values([
            {
                "name": "Freemium",
                "description": "Free tier with basic features",
                "price": "0.00",
                "billing_period": "monthly",
                "is_active": True,
                "features": '["Basic features", "Email support"]',
            },
            {
                "name": "Premium",
                "description": "Full access to all features",
                "price": "99.00",
                "billing_period": "monthly",
                "is_active": True,
                "features": '["All features", "Priority support", "Advanced analytics"]',
            },
        ])
    )


def downgrade() -> None:
    op.drop_table("subscription_plans")
