"""Add is_due and is_overdue boolean columns to fee_installments

Revision ID: add_is_due_is_overdue_columns
Revises: 5cc50cad6579
Create Date: 2026-04-11 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'add_is_due_is_overdue_columns'
down_revision: Union[str, Sequence[str], None] = '5cc50cad6579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_due and is_overdue boolean columns to fee_installments table."""
    with op.batch_alter_table('fee_installments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_due', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('is_overdue', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove is_due and is_overdue columns from fee_installments table."""
    with op.batch_alter_table('fee_installments', schema=None) as batch_op:
        batch_op.drop_column('is_overdue')
        batch_op.drop_column('is_due')
