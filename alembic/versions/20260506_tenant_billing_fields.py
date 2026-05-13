"""tenants: add billing_type and payment_date

Revision ID: 20260506_tenant_billing
Revises: 20260504_tenant_subscription
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260506_tenant_billing"
down_revision: Union[str, Sequence[str], None] = "20260504_tenant_subscription"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("billing_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("payment_date", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "payment_date")
    op.drop_column("tenants", "billing_type")
