"""add_is_matricule_format_set_to_tenant_settings

Revision ID: 9f32521d46ef
Revises: 1182b3b37d1c
Create Date: 2026-03-01 15:17:18.180887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f32521d46ef'
down_revision: Union[str, Sequence[str], None] = '1182b3b37d1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_matricule_format_set column to tenant_settings table
    op.add_column('tenant_settings', sa.Column('is_matricule_format_set', sa.Boolean(), nullable=False, server_default='0'))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Remove is_matricule_format_set column from tenant_settings table
    op.drop_column('tenant_settings', 'is_matricule_format_set')
    # ### end Alembic commands ###
