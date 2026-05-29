"""subscription_services: is_monetized_enabled for pay-per-use services

Revision ID: 20260531_sub_svc_monetization
Revises: 20260530_grading_gpa
Create Date: 2026-05-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260531_sub_svc_monetization"
down_revision: Union[str, Sequence[str], None] = "20260530_grading_gpa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "subscription_services" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("subscription_services")}
    if "is_monetized_enabled" not in cols:
        op.add_column(
            "subscription_services",
            sa.Column(
                "is_monetized_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "subscription_services" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("subscription_services")}
    if "is_monetized_enabled" in cols:
        op.drop_column("subscription_services", "is_monetized_enabled")
