"""Add place_of_birth and degree_proposed to students table

Revision ID: 20260412_01_add_student_birthplace_degree
Revises: 
Create Date: 2026-04-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260412_01_add_student_birthplace_degree'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('students', sa.Column('place_of_birth', sa.String(200), nullable=True))
    op.add_column('students', sa.Column('degree_proposed', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('students', 'degree_proposed')
    op.drop_column('students', 'place_of_birth')
