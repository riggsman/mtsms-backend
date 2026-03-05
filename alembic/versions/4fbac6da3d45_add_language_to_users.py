"""add language to users

Revision ID: 4fbac6da3d45
Revises: b58d402c7562
Create Date: 2026-03-05 10:52:37.189665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '4fbac6da3d45'
down_revision: Union[str, Sequence[str], None] = 'b58d402c7562'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add language column to users table."""
    # Add language column with default value 'en'
    op.add_column(
        'users',
        sa.Column(
            'language',
            mysql.VARCHAR(length=8),
            nullable=False,
            server_default='en'
        )
    )
    # Remove server default after adding the column (optional, but cleaner)
    # This allows the application to set the value explicitly
    op.alter_column('users', 'language', server_default=None)


def downgrade() -> None:
    """Remove language column from users table."""
    op.drop_column('users', 'language')
