"""tenant_settings: enabled_program_levels JSON

Revision ID: 20260532_tenant_prog_levels
Revises: 20260531_sub_svc_monetization
Create Date: 2026-05-32
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260532_tenant_prog_levels"
down_revision: Union[str, Sequence[str], None] = "20260531_sub_svc_monetization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "tenant_settings" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tenant_settings")}
    if "enabled_program_levels" not in cols:
        op.add_column(
            "tenant_settings",
            sa.Column("enabled_program_levels", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "tenant_settings" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tenant_settings")}
    if "enabled_program_levels" in cols:
        op.drop_column("tenant_settings", "enabled_program_levels")
