"""create_tenant_settings_table

Revision ID: 4e6855bbaad4
Revises: 0b83af8e822e
Create Date: 2026-02-25 10:05:30.414959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '4e6855bbaad4'
down_revision: Union[str, Sequence[str], None] = '0b83af8e822e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenant_settings table."""
    op.create_table('tenant_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('matricule_format', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenant_settings_id'), 'tenant_settings', ['id'], unique=False)
    op.create_index(op.f('ix_tenant_settings_institution_id'), 'tenant_settings', ['institution_id'], unique=True)


def downgrade() -> None:
    """Drop tenant_settings table."""
    op.drop_index(op.f('ix_tenant_settings_institution_id'), table_name='tenant_settings')
    op.drop_index(op.f('ix_tenant_settings_id'), table_name='tenant_settings')
    op.drop_table('tenant_settings')
