"""add instructor_id to courses

Revision ID: 20260509_add_instructor_id
Revises: 20260509_course_performance_dates
Create Date: 2026-05-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260509_add_instructor_id"
down_revision: Union[str, Sequence[str], None] = "20260509_course_performance_dates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "courses" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("courses")}
    if "instructor_id" in columns:
        return

    with op.batch_alter_table("courses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("instructor_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "courses" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("courses")}
    if "instructor_id" not in columns:
        return

    with op.batch_alter_table("courses", schema=None) as batch_op:
        batch_op.drop_column("instructor_id")
