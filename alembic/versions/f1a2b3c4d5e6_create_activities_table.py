"""create_activities_table

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: str = 'a1b2c3d4e5f6'  # Update this to the latest migration
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('performed_by', sa.String(length=200), nullable=False),
        sa.Column('performer_role', sa.String(length=50), nullable=False),
        sa.Column('performer_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_id'), 'activities', ['id'], unique=False)
    op.create_index(op.f('ix_activities_institution_id'), 'activities', ['institution_id'], unique=False)
    op.create_index(op.f('ix_activities_created_at'), 'activities', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_activities_created_at'), table_name='activities')
    op.drop_index(op.f('ix_activities_institution_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_id'), table_name='activities')
    op.drop_table('activities')
