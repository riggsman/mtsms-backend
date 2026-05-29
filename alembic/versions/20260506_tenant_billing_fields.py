"""tenants: add billing_type and payment_date

Revision ID: 20260506_tenant_billing
Revises: 20260504_tenant_subscription
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260506_tenant_billing"
down_revision: Union[str, Sequence[str], None] = "20260504_tenant_subscription"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "tenants" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "billing_type" not in columns:
        op.add_column(
            "tenants",
            sa.Column("billing_type", sa.String(length=20), nullable=True),
        )
    if "payment_date" not in columns:
        op.add_column(
            "tenants",
            sa.Column("payment_date", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "tenants" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "payment_date" in columns:
        op.drop_column("tenants", "payment_date")
    if "billing_type" in columns:
        op.drop_column("tenants", "billing_type")
