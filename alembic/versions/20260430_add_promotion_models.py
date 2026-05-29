"""add student year outcomes and promotion history tables

Revision ID: 20260430_promotion_models
Revises: add_firebase_service_uploaded
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260430_promotion_models"
down_revision: Union[str, Sequence[str], None] = "add_firebase_service_uploaded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "student_year_outcomes" not in tables:
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

    _create_index_if_missing(
        "student_year_outcomes",
        "ix_student_year_outcomes_institution_id",
        ["institution_id"],
    )
    _create_index_if_missing(
        "student_year_outcomes",
        "ix_student_year_outcomes_student_id",
        ["student_id"],
    )
    _create_index_if_missing(
        "student_year_outcomes",
        "ix_student_year_outcomes_academic_year_id",
        ["academic_year_id"],
    )
    _create_index_if_missing(
        "student_year_outcomes",
        "ix_student_year_outcomes_final_status",
        ["final_status"],
    )

    if "student_promotion_history" not in tables:
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

    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_institution_id",
        ["institution_id"],
    )
    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_student_id",
        ["student_id"],
    )
    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_academic_year_id",
        ["academic_year_id"],
    )
    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_from_class_id",
        ["from_class_id"],
    )
    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_to_class_id",
        ["to_class_id"],
    )
    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_final_status",
        ["final_status"],
    )
    _create_index_if_missing(
        "student_promotion_history",
        "ix_student_promotion_history_execution_id",
        ["execution_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "student_promotion_history" in tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("student_promotion_history")}
        for name in [
            "ix_student_promotion_history_execution_id",
            "ix_student_promotion_history_final_status",
            "ix_student_promotion_history_to_class_id",
            "ix_student_promotion_history_from_class_id",
            "ix_student_promotion_history_academic_year_id",
            "ix_student_promotion_history_student_id",
            "ix_student_promotion_history_institution_id",
        ]:
            if name in indexes:
                op.drop_index(name, table_name="student_promotion_history")
        op.drop_table("student_promotion_history")

    if "student_year_outcomes" in tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("student_year_outcomes")}
        for name in [
            "ix_student_year_outcomes_final_status",
            "ix_student_year_outcomes_academic_year_id",
            "ix_student_year_outcomes_student_id",
            "ix_student_year_outcomes_institution_id",
        ]:
            if name in indexes:
                op.drop_index(name, table_name="student_year_outcomes")
        op.drop_table("student_year_outcomes")
