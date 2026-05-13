"""add student course ranks table

Revision ID: 20260430_student_course_ranks
Revises: 20260430_promotion_models
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260430_student_course_ranks"
down_revision: Union[str, Sequence[str], None] = "20260430_promotion_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("student_course_ranks"):
        # Table already present (manual create, failed mid-migration, or duplicate env).
        # Skip DDL so Alembic can stamp this revision without error.
        return

    op.create_table(
        "student_course_ranks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=70), nullable=False),
        sa.Column("course_code", sa.String(length=50), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=False),
        sa.Column("semester_or_term", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("dense_rank", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "institution_id",
            "student_id",
            "course_code",
            "academic_year",
            "semester_or_term",
            name="uq_student_course_rank_scope",
        ),
        sa.CheckConstraint("dense_rank >= 1", name="ck_student_course_rank_dense_rank_positive"),
    )

    op.create_index(
        "ix_student_course_ranks_scope_rank",
        "student_course_ranks",
        ["institution_id", "course_code", "academic_year", "semester_or_term", "dense_rank"],
    )
    op.create_index(
        "ix_student_course_ranks_student_scope",
        "student_course_ranks",
        ["institution_id", "student_id", "academic_year", "semester_or_term"],
    )
    op.create_index(
        "ix_student_course_ranks_computed_at",
        "student_course_ranks",
        ["institution_id", "computed_at"],
    )
    op.create_index("ix_student_course_ranks_institution_id", "student_course_ranks", ["institution_id"])
    op.create_index("ix_student_course_ranks_student_id", "student_course_ranks", ["student_id"])
    op.create_index("ix_student_course_ranks_course_code", "student_course_ranks", ["course_code"])
    op.create_index("ix_student_course_ranks_academic_year", "student_course_ranks", ["academic_year"])
    op.create_index("ix_student_course_ranks_semester_or_term", "student_course_ranks", ["semester_or_term"])
    op.create_index("ix_student_course_ranks_dense_rank", "student_course_ranks", ["dense_rank"])
    op.create_index("ix_student_course_ranks_computed_at_single", "student_course_ranks", ["computed_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("student_course_ranks"):
        return

    op.drop_index("ix_student_course_ranks_computed_at_single", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_dense_rank", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_semester_or_term", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_academic_year", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_course_code", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_student_id", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_institution_id", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_computed_at", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_student_scope", table_name="student_course_ranks")
    op.drop_index("ix_student_course_ranks_scope_rank", table_name="student_course_ranks")
    op.drop_table("student_course_ranks")
