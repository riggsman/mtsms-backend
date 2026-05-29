"""Add kind/side columns to student uploaded documents.

Revision ID: 20260605_student_doc_kind_side
Revises: 20260605_student_uploaded_docume
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260605_student_doc_kind_side"
down_revision = "20260605_student_uploaded_docume"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "student_uploaded_documents" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("student_uploaded_documents")}
    if "document_kind" not in columns:
        op.add_column(
            "student_uploaded_documents",
            sa.Column("document_kind", sa.String(length=40), nullable=False, server_default="general"),
        )
    if "document_side" not in columns:
        op.add_column(
            "student_uploaded_documents",
            sa.Column("document_side", sa.String(length=20), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "student_uploaded_documents" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("student_uploaded_documents")}
    if "document_side" in columns:
        op.drop_column("student_uploaded_documents", "document_side")
    if "document_kind" in columns:
        op.drop_column("student_uploaded_documents", "document_kind")
