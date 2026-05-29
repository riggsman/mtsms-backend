"""payroll_time_entries: when clock codes were consumed (audit)

Revision ID: 20260501_payroll_code_used
Revises: 20260430_student_course_ranks
Create Date: 2026-05-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260501_payroll_code_used"
down_revision: Union[str, Sequence[str], None] = "20260430_student_course_ranks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "payroll_time_entries" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("payroll_time_entries")}
    if "clock_in_code_used_at" not in columns:
        op.add_column(
            "payroll_time_entries",
            sa.Column("clock_in_code_used_at", sa.DateTime(), nullable=True),
        )
    if "clock_out_code_used_at" not in columns:
        op.add_column(
            "payroll_time_entries",
            sa.Column("clock_out_code_used_at", sa.DateTime(), nullable=True),
        )

    op.execute(
        """
        UPDATE payroll_time_entries
        SET clock_in_code_used_at = clock_in_at
        WHERE clock_in_code_hash IS NULL
          AND clock_in_code_used_at IS NULL
          AND codes_generated_at IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE payroll_time_entries
        SET clock_out_code_used_at = COALESCE(
            lecturer_clock_out_confirmed_at,
            student_clock_out_confirmed_at
        )
        WHERE clock_out_code_hash IS NULL
          AND clock_out_code_used_at IS NULL
          AND codes_generated_at IS NOT NULL
          AND (
            lecturer_clock_out_confirmed_at IS NOT NULL
            OR student_clock_out_confirmed_at IS NOT NULL
          )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "payroll_time_entries" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("payroll_time_entries")}
    if "clock_out_code_used_at" in columns:
        op.drop_column("payroll_time_entries", "clock_out_code_used_at")
    if "clock_in_code_used_at" in columns:
        op.drop_column("payroll_time_entries", "clock_in_code_used_at")
