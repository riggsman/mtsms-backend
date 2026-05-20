"""Tenant services activation flag and platform support contact fields."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260527_tenant_services"
down_revision: Union[str, Sequence[str], None] = "20260526_cal_date_range"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tenant_cols = {c["name"] for c in insp.get_columns("tenants")}
    if "services_activated" not in tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("services_activated", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "services_activated_at" not in tenant_cols:
        op.add_column("tenants", sa.Column("services_activated_at", sa.DateTime(), nullable=True))
    if "services_activated_by" not in tenant_cols:
        op.add_column("tenants", sa.Column("services_activated_by", sa.Integer(), nullable=True))

    settings_cols = {c["name"] for c in insp.get_columns("system_settings")}
    if "platform_support_email" not in settings_cols:
        op.add_column("system_settings", sa.Column("platform_support_email", sa.String(255), nullable=True))
    if "platform_support_phone" not in settings_cols:
        op.add_column("system_settings", sa.Column("platform_support_phone", sa.String(50), nullable=True))
    if "platform_support_hours" not in settings_cols:
        op.add_column("system_settings", sa.Column("platform_support_hours", sa.String(255), nullable=True))

    # Existing tenants with enabled entitlements are treated as already live.
    op.execute(
        """
        UPDATE tenants AS t
        SET services_activated = true
        WHERE EXISTS (
            SELECT 1 FROM tenant_feature_entitlements AS e
            WHERE e.tenant_id = t.id AND e.is_enabled = true
        )
        """
    )


def downgrade() -> None:
    op.drop_column("system_settings", "platform_support_hours")
    op.drop_column("system_settings", "platform_support_phone")
    op.drop_column("system_settings", "platform_support_email")
    op.drop_column("tenants", "services_activated_by")
    op.drop_column("tenants", "services_activated_at")
    op.drop_column("tenants", "services_activated")
