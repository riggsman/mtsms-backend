"""added type and deparment fields

Revision ID: 6f398db6a875
Revises: acb5afbc8d7d
Create Date: 2026-04-10 12:12:46.473916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '6f398db6a875'
down_revision: Union[str, Sequence[str], None] = 'acb5afbc8d7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # These tables were already dropped in revision acb5afbc8d7d
    # Adding the new 'type' column to students
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.add_column(sa.Column('type', sa.String(length=20), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.drop_column('type')
