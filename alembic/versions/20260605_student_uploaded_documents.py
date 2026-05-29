"""Create student uploaded documents table.

Revision ID: 20260605_student_uploaded_docume
Revises: 20260604_service_usage_and_free_limit
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260605_student_uploaded_docume"
down_revision = "20260604_service_usage_and_free_limit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "student_uploaded_documents" not in inspector.get_table_names():
        op.create_table(
            "student_uploaded_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("file_path", sa.String(length=500), nullable=False),
            sa.Column("mime_type", sa.String(length=120), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_student_uploaded_documents_institution_id",
            "student_uploaded_documents",
            ["institution_id"],
        )
        op.create_index(
            "ix_student_uploaded_documents_student_id",
            "student_uploaded_documents",
            ["student_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "student_uploaded_documents" in inspector.get_table_names():
        op.drop_index(
            "ix_student_uploaded_documents_student_id",
            table_name="student_uploaded_documents",
        )
        op.drop_index(
            "ix_student_uploaded_documents_institution_id",
            table_name="student_uploaded_documents",
        )
        op.drop_table("student_uploaded_documents")
