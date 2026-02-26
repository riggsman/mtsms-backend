"""add_lecturer_id_and_max_score_to_assignments

Revision ID: a9b8c7d6e5f4
Revises: 48b8a8d7b05d
Create Date: 2026-02-24 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = '48b8a8d7b05d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add lecturer_id and max_score columns to assignments table."""
    # Add lecturer_id column (nullable, with index)
    op.add_column('assignments', sa.Column('lecturer_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_assignments_lecturer_id'), 'assignments', ['lecturer_id'], unique=False)
    
    # Add max_score column (nullable, Numeric(10, 2))
    op.add_column('assignments', sa.Column('max_score', mysql.NUMERIC(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """Remove lecturer_id and max_score columns from assignments table."""
    op.drop_index(op.f('ix_assignments_lecturer_id'), table_name='assignments')
    op.drop_column('assignments', 'lecturer_id')
    op.drop_column('assignments', 'max_score')
