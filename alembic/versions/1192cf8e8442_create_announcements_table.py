"""create_announcements_table

Revision ID: 1192cf8e8442
Revises: 512037db5b96
Create Date: 2026-02-25 11:18:26.553721

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '1192cf8e8442'
down_revision: Union[str, Sequence[str], None] = '512037db5b96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create announcements table
    op.create_table('announcements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('institution_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_announcements_id'), 'announcements', ['id'], unique=False)
    op.create_index(op.f('ix_announcements_institution_id'), 'announcements', ['institution_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_announcements_institution_id'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_id'), table_name='announcements')
    op.drop_table('announcements')
