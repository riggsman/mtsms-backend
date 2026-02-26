"""add_code_and_institution_level_to_classes

Revision ID: 48b8a8d7b05d
Revises: ff546592286b
Create Date: 2026-02-24 14:16:09.715068

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48b8a8d7b05d'
down_revision: Union[str, Sequence[str], None] = 'ff546592286b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add code, institution_level, and is_custom fields to classes table, make level_id and academic_year_id nullable."""
    # Add code column
    op.add_column('classes', sa.Column('code', sa.String(length=20), nullable=False, server_default=''))
    
    # Add institution_level column with default 'HI'
    op.add_column('classes', sa.Column('institution_level', sa.String(length=10), nullable=False, server_default='HI'))
    
    # Add is_custom column to distinguish custom vs default classes
    op.add_column('classes', sa.Column('is_custom', sa.Boolean(), nullable=False, server_default='1'))
    
    # Make level_id nullable
    op.alter_column('classes', 'level_id',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_nullable=False)
    
    # Make academic_year_id nullable
    op.alter_column('classes', 'academic_year_id',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_nullable=False)
    
    # Remove server defaults after adding columns
    op.alter_column('classes', 'code', server_default=None)
    op.alter_column('classes', 'institution_level', server_default=None)
    op.alter_column('classes', 'is_custom', server_default=None)


def downgrade() -> None:
    """Remove code, institution_level, and is_custom fields, make level_id and academic_year_id non-nullable."""
    # Make academic_year_id non-nullable (with default value)
    op.alter_column('classes', 'academic_year_id',
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_nullable=True,
                    server_default='1')
    
    # Make level_id non-nullable (with default value)
    op.alter_column('classes', 'level_id',
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_nullable=True,
                    server_default='1')
    
    # Drop is_custom column
    op.drop_column('classes', 'is_custom')
    
    # Drop institution_level column
    op.drop_column('classes', 'institution_level')
    
    # Drop code column
    op.drop_column('classes', 'code')
    
    # Remove server defaults
    op.alter_column('classes', 'academic_year_id', server_default=None)
    op.alter_column('classes', 'level_id', server_default=None)
