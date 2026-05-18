"""Backfill premium tenant payment_date, subscription_started_at, billing_type

Revision ID: 20260519_premium_billing
Revises: 20260518_sub_svc_button_id
Create Date: 2026-05-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_premium_billing"
down_revision: Union[str, Sequence[str], None] = "20260518_sub_svc_button_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "tenants" not in insp.get_table_names():
        return

    # Premium tenants: ensure payment_date from subscription_started_at or created_at
    bind.execute(
        sa.text(
            """
            UPDATE tenants
            SET payment_date = COALESCE(payment_date, subscription_started_at, created_at)
            WHERE subscription_plan IS NOT NULL
              AND LOWER(TRIM(subscription_plan)) LIKE '%premium%'
              AND payment_date IS NULL
            """
        )
    )

    # Align subscription_started_at with payment date when missing
    bind.execute(
        sa.text(
            """
            UPDATE tenants
            SET subscription_started_at = COALESCE(subscription_started_at, payment_date, created_at)
            WHERE subscription_plan IS NOT NULL
              AND LOWER(TRIM(subscription_plan)) LIKE '%premium%'
              AND subscription_started_at IS NULL
            """
        )
    )

    # Default billing_type for display when unset
    bind.execute(
        sa.text(
            """
            UPDATE tenants
            SET billing_type = 'monthly'
            WHERE subscription_plan IS NOT NULL
              AND LOWER(TRIM(subscription_plan)) LIKE '%premium%'
              AND (billing_type IS NULL OR TRIM(billing_type) = '')
            """
        )
    )


def downgrade() -> None:
    pass
