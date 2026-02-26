"""add photo to student

Revision ID: a1b2c3d4e5f6
Revises: 6b521dd72d82
Create Date: 2024-01-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6b521dd72d82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add photo column to students table
    op.add_column('students', sa.Column('photo', sa.String(length=5000), nullable=True))


def downgrade() -> None:
    # Remove photo column from students table
    op.drop_column('students', 'photo')
