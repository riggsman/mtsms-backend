"""tenant_feature_entitlements table

Revision ID: 20260521_tenant_features
Revises: 20260520_tenant_billing_rem
Create Date: 2026-05-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_tenant_features"
down_revision: Union[str, Sequence[str], None] = "20260520_tenant_billing_rem"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "tenant_feature_entitlements" in insp.get_table_names():
        return
    op.create_table(
        "tenant_feature_entitlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("button_id", sa.String(length=120), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index(
        "ix_tenant_feature_entitlements_tenant_id",
        "tenant_feature_entitlements",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_feature_entitlement_unique",
        "tenant_feature_entitlements",
        ["tenant_id", "button_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_feature_entitlement_unique", table_name="tenant_feature_entitlements")
    op.drop_index("ix_tenant_feature_entitlements_tenant_id", table_name="tenant_feature_entitlements")
    op.drop_table("tenant_feature_entitlements")
