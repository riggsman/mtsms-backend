"""add instructor_id to courses

Revision ID: 20260509_add_instructor_id
Revises: 20260509_course_performance_dates
Create Date: 2026-05-09 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260509_add_instructor_id'
down_revision = '20260509_course_performance_dates'
branch_labels = None
depends_on = None


def upgrade():
    # Add instructor_id to courses table
    # Using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instructor_id', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('instructor_id')
