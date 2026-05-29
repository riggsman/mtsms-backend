"""create subscription_plans table and seed default plans

Revision ID: 20260506_subscription_plans
Revises: 20260506_tenant_billing
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260506_subscription_plans"
down_revision: Union[str, Sequence[str], None] = "20260506_tenant_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    if "subscription_plans" not in tables:
        op.create_table(
            "subscription_plans",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=64), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("billing_period", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("features", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    existing_names = set()
    if "subscription_plans" in set(inspect(bind).get_table_names()):
        rows = bind.execute(sa.text("SELECT name FROM subscription_plans")).fetchall()
        existing_names = {row[0] for row in rows}

    seed_rows = [
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
    ]

    for row in seed_rows:
        if row["name"] in existing_names:
            continue
        op.execute(
            sa.text(
                """
                INSERT INTO subscription_plans
                    (name, description, price, billing_period, is_active, features)
                VALUES
                    (:name, :description, :price, :billing_period, :is_active, :features)
                """
            ),
            row,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "subscription_plans" in insp.get_table_names():
        op.drop_table("subscription_plans")
