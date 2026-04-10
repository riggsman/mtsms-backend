"""Add department_id and position fields to users.

Revision ID: 20260330_01
Revises: fcaca6ae897b
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260330_01"
down_revision: Union[str, Sequence[str], None] = "fcaca6ae897b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("department_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("position", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("position")
        batch_op.drop_column("department_id")

