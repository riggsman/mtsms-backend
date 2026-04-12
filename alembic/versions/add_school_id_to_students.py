"""Add school_id foreign key to students table

Revision ID: add_school_id_to_students
Revises: 
Create Date: 2026-04-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_school_id_to_students'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('students', sa.Column('school_id', sa.Integer(), sa.ForeignKey('schools.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('students', 'school_id')
