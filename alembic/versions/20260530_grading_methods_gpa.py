"""grading methods, ranges, and student record course weight

Revision ID: 20260530_grading_gpa
Revises: 20260529_seed_superadmin
Create Date: 2026-05-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260530_grading_gpa"
down_revision: Union[str, Sequence[str], None] = "20260529_seed_superadmin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_GRADING_RANGES = [
    {"minimum_score": 0.0, "maximum_score": 59.99, "grade": "F", "grade_point": 0.0},
    {"minimum_score": 60.0, "maximum_score": 69.99, "grade": "D", "grade_point": 1.0},
    {"minimum_score": 70.0, "maximum_score": 79.99, "grade": "C", "grade_point": 2.0},
    {"minimum_score": 80.0, "maximum_score": 89.99, "grade": "B", "grade_point": 3.0},
    {"minimum_score": 90.0, "maximum_score": 100.0, "grade": "A", "grade_point": 4.0},
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "grading_methods" not in tables:
        op.create_table(
            "grading_methods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=True),
            sa.Column("is_system_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("institution_id", name="uq_grading_methods_institution_id"),
        )

    if "grading_ranges" not in tables:
        op.create_table(
            "grading_ranges",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("grading_method_id", sa.Integer(), sa.ForeignKey("grading_methods.id", ondelete="CASCADE"), nullable=False),
            sa.Column("minimum_score", sa.Float(), nullable=False),
            sa.Column("maximum_score", sa.Float(), nullable=False),
            sa.Column("grade", sa.String(length=10), nullable=False),
            sa.Column("grade_point", sa.Float(), nullable=False),
        )

    student_record_columns = {col["name"] for col in inspector.get_columns("student_records")}
    if "course_weight" not in student_record_columns:
        op.add_column(
            "student_records",
            sa.Column("course_weight", sa.Numeric(precision=3, scale=1), nullable=True, server_default="1.0"),
        )

    conn = op.get_bind()
    existing_default = conn.execute(
        sa.text("SELECT id FROM grading_methods WHERE is_system_default = 1 LIMIT 1")
    ).fetchone()

    if not existing_default:
        conn.execute(
            sa.text(
                "INSERT INTO grading_methods (name, institution_id, is_system_default, created_at) "
                "VALUES (:name, NULL, 1, CURRENT_TIMESTAMP)"
            ),
            {"name": "System Default (4.0 Scale)"},
        )
        method_id = conn.execute(
            sa.text("SELECT id FROM grading_methods WHERE is_system_default = 1 LIMIT 1")
        ).scalar()

        for row in DEFAULT_GRADING_RANGES:
            conn.execute(
                sa.text(
                    "INSERT INTO grading_ranges "
                    "(grading_method_id, minimum_score, maximum_score, grade, grade_point) "
                    "VALUES (:method_id, :minimum_score, :maximum_score, :grade, :grade_point)"
                ),
                {"method_id": method_id, **row},
            )

    conn.execute(
        sa.text(
            "UPDATE student_records SET course_weight = 1.0 "
            "WHERE course_weight IS NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    student_record_columns = {col["name"] for col in inspector.get_columns("student_records")}
    if "course_weight" in student_record_columns:
        op.drop_column("student_records", "course_weight")

    tables = set(inspector.get_table_names())
    if "grading_ranges" in tables:
        op.drop_table("grading_ranges")
    if "grading_methods" in tables:
        op.drop_table("grading_methods")
