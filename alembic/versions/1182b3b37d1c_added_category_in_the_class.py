"""added category in the class

Revision ID: 1182b3b37d1c
Revises: 9ff4fe6f7a44
Create Date: 2026-02-28 09:35:45.103860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '1182b3b37d1c'
down_revision: Union[str, Sequence[str], None] = '9ff4fe6f7a44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add category column to classes table
    op.add_column('classes', sa.Column('category', sa.String(length=50), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Remove category column from classes table
    op.drop_column('classes', 'category')
    # ### end Alembic commands ###
