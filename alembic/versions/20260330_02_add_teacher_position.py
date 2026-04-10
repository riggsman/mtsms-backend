"""Add position field to teachers.

Revision ID: 20260330_02
Revises: 20260330_01
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260330_02"
down_revision: Union[str, Sequence[str], None] = "20260330_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("position", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.drop_column("position")

