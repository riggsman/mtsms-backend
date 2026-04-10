"""Payment indexes; align branches server defaults with ORM models.

Branch tables/columns (branches, branch_id, branches_enabled) are created in
20260324_01 — do not duplicate that DDL here.

Revision ID: fcaca6ae897b
Revises: 20260324_01
Create Date: 2026-03-24 20:50:01.718441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "fcaca6ae897b"
down_revision: Union[str, Sequence[str], None] = "20260324_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("branches", schema=None) as batch_op:
        batch_op.alter_column(
            "sort_order",
            existing_type=mysql.INTEGER(display_width=11),
            server_default=None,
            existing_nullable=False,
        )
        batch_op.alter_column(
            "is_active",
            existing_type=mysql.TINYINT(display_width=1),
            server_default=None,
            existing_nullable=False,
        )

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.create_index("ix_payment_created", ["created_at"], unique=False)
        batch_op.create_index(
            "ix_payment_institution_status",
            ["institution_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_index("ix_payment_institution_status")
        batch_op.drop_index("ix_payment_created")

    with op.batch_alter_table("branches", schema=None) as batch_op:
        batch_op.alter_column(
            "is_active",
            existing_type=mysql.TINYINT(display_width=1),
            server_default=sa.text("1"),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "sort_order",
            existing_type=mysql.INTEGER(display_width=11),
            server_default=sa.text("0"),
            existing_nullable=False,
        )
