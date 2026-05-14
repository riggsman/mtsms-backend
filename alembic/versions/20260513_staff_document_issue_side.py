"""staff_documents: add issue date and document side

Revision ID: 20260513_staff_doc_issue_side
Revises: 20260509_add_instructor_id
Create Date: 2026-05-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260513_staff_doc_issue_side"
down_revision: Union[str, Sequence[str], None] = "20260509_add_instructor_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("staff_documents")}
    if "issue_date" not in columns:
        op.add_column("staff_documents", sa.Column("issue_date", sa.DateTime(), nullable=True))
    if "document_side" not in columns:
        op.add_column("staff_documents", sa.Column("document_side", sa.String(length=20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("staff_documents")}
    if "document_side" in columns:
        op.drop_column("staff_documents", "document_side")
    if "issue_date" in columns:
        op.drop_column("staff_documents", "issue_date")
