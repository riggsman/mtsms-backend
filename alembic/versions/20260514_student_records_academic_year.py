"""student_records: add academic year

Revision ID: 20260514_student_rec_acad_year
Revises: 20260513_staff_doc_issue_side
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260514_student_rec_acad_year"
down_revision: Union[str, Sequence[str], None] = "20260513_staff_doc_issue_side"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("student_records")}
    if "academic_year" not in columns:
        op.add_column("student_records", sa.Column("academic_year", sa.String(length=50), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("student_records")}
    if "academic_year" in columns:
        op.drop_column("student_records", "academic_year")
