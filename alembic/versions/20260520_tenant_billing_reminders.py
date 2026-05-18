"""tenant_billing_reminders table

Revision ID: 20260520_tenant_billing_rem
Revises: 20260519_premium_billing
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_tenant_billing_rem"
down_revision: Union[str, Sequence[str], None] = "20260519_premium_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "tenant_billing_reminders" in insp.get_table_names():
        return
    op.create_table(
        "tenant_billing_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("billing_due_date", sa.DateTime(), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_tenant_billing_reminders_tenant_id", "tenant_billing_reminders", ["tenant_id"])
    op.create_index(
        "ix_tenant_billing_reminder_unique",
        "tenant_billing_reminders",
        ["tenant_id", "billing_due_date"],
        unique=True,
    )

    if "tenants" in insp.get_table_names() and "subscription_plans" in insp.get_table_names():
        bind.execute(
            sa.text(
                """
                UPDATE tenants t
                INNER JOIN subscription_plans sp ON sp.name = t.subscription_plan
                SET t.billing_type = sp.billing_period
                WHERE t.subscription_plan IS NOT NULL
                  AND sp.billing_period IS NOT NULL
                  AND (t.billing_type IS NULL OR TRIM(t.billing_type) = '')
                """
            )
        )


def downgrade() -> None:
    op.drop_index("ix_tenant_billing_reminder_unique", table_name="tenant_billing_reminders")
    op.drop_index("ix_tenant_billing_reminders_tenant_id", table_name="tenant_billing_reminders")
    op.drop_table("tenant_billing_reminders")
