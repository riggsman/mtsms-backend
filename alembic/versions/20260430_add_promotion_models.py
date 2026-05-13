"""add student year outcomes and promotion history tables

Revision ID: 20260430_promotion_models
Revises: add_firebase_service_uploaded
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260430_promotion_models"
down_revision: Union[str, Sequence[str], None] = "add_firebase_service_uploaded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_year_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=20), nullable=True),
        sa.Column("final_status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.Integer(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "institution_id",
            "student_id",
            "academic_year_id",
            name="uq_student_year_outcomes_student_year",
        ),
    )
    op.create_index(
        "ix_student_year_outcomes_institution_id",
        "student_year_outcomes",
        ["institution_id"],
    )
    op.create_index(
        "ix_student_year_outcomes_student_id",
        "student_year_outcomes",
        ["student_id"],
    )
    op.create_index(
        "ix_student_year_outcomes_academic_year_id",
        "student_year_outcomes",
        ["academic_year_id"],
    )
    op.create_index(
        "ix_student_year_outcomes_final_status",
        "student_year_outcomes",
        ["final_status"],
    )

    op.create_table(
        "student_promotion_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("from_class_id", sa.Integer(), nullable=False),
        sa.Column("to_class_id", sa.Integer(), nullable=True),
        sa.Column("final_status", sa.String(length=30), nullable=False),
        sa.Column("archived_student_snapshot", sa.Text(), nullable=True),
        sa.Column("archived_enrollment_snapshot", sa.Text(), nullable=True),
        sa.Column("promoted_by", sa.Integer(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(), nullable=False),
        sa.Column("execution_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "institution_id",
            "student_id",
            "academic_year_id",
            "final_status",
            name="uq_student_promotion_history_idempotency",
        ),
    )
    op.create_index(
        "ix_student_promotion_history_institution_id",
        "student_promotion_history",
        ["institution_id"],
    )
    op.create_index(
        "ix_student_promotion_history_student_id",
        "student_promotion_history",
        ["student_id"],
    )
    op.create_index(
        "ix_student_promotion_history_academic_year_id",
        "student_promotion_history",
        ["academic_year_id"],
    )
    op.create_index(
        "ix_student_promotion_history_from_class_id",
        "student_promotion_history",
        ["from_class_id"],
    )
    op.create_index(
        "ix_student_promotion_history_to_class_id",
        "student_promotion_history",
        ["to_class_id"],
    )
    op.create_index(
        "ix_student_promotion_history_final_status",
        "student_promotion_history",
        ["final_status"],
    )
    op.create_index(
        "ix_student_promotion_history_execution_id",
        "student_promotion_history",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_promotion_history_execution_id", table_name="student_promotion_history")
    op.drop_index("ix_student_promotion_history_final_status", table_name="student_promotion_history")
    op.drop_index("ix_student_promotion_history_to_class_id", table_name="student_promotion_history")
    op.drop_index("ix_student_promotion_history_from_class_id", table_name="student_promotion_history")
    op.drop_index("ix_student_promotion_history_academic_year_id", table_name="student_promotion_history")
    op.drop_index("ix_student_promotion_history_student_id", table_name="student_promotion_history")
    op.drop_index("ix_student_promotion_history_institution_id", table_name="student_promotion_history")
    op.drop_table("student_promotion_history")

    op.drop_index("ix_student_year_outcomes_final_status", table_name="student_year_outcomes")
    op.drop_index("ix_student_year_outcomes_academic_year_id", table_name="student_year_outcomes")
    op.drop_index("ix_student_year_outcomes_student_id", table_name="student_year_outcomes")
    op.drop_index("ix_student_year_outcomes_institution_id", table_name="student_year_outcomes")
    op.drop_table("student_year_outcomes")
