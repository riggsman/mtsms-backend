"""courses: add performance tracking dates

Revision ID: 20260509_course_performance_dates
Revises: 20260506_subscription_plans
Create Date: 2026-05-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260509_course_performance_dates"
down_revision: Union[str, Sequence[str], None] = "20260506_subscription_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("courses")}
    if "start_date" not in columns:
        op.add_column("courses", sa.Column("start_date", sa.Date(), nullable=True))
    if "expected_end_date" not in columns:
        op.add_column("courses", sa.Column("expected_end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("courses")}
    if "expected_end_date" in columns:
        op.drop_column("courses", "expected_end_date")
    if "start_date" in columns:
        op.drop_column("courses", "start_date")
