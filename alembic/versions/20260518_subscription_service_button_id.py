"""subscription_services: button_id for feature catalog linkage

Revision ID: 20260518_sub_svc_button_id
Revises: 20260517_stu_chat_dm
Create Date: 2026-05-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260518_sub_svc_button_id"
down_revision: Union[str, Sequence[str], None] = "20260517_stu_chat_dm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "subscription_services" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("subscription_services")}
    if "button_id" not in cols:
        op.add_column(
            "subscription_services",
            sa.Column("button_id", sa.String(length=120), nullable=True),
        )
        op.create_index(
            "ix_subscription_services_button_id",
            "subscription_services",
            ["button_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "subscription_services" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("subscription_services")}
    if "button_id" in cols:
        op.drop_index("ix_subscription_services_button_id", table_name="subscription_services")
        op.drop_column("subscription_services", "button_id")
