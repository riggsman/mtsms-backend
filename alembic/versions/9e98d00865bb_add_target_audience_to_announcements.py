"""add_target_audience_to_announcements

Revision ID: 9e98d00865bb
Revises: 1192cf8e8442
Create Date: 2026-02-25 11:26:14.842538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '9e98d00865bb'
down_revision: Union[str, Sequence[str], None] = '1192cf8e8442'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add target_audience column to announcements table
    op.add_column('announcements', sa.Column('target_audience', sa.String(length=20), nullable=False, server_default='all'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('announcements', 'target_audience')
