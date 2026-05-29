"""Add verified_documents table for transcript/result slip QR verification."""
from alembic import op
import sqlalchemy as sa

revision = "20260603_verified_documents"
down_revision = "20260602_class_degree_programs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "verified_documents" in inspector.get_table_names():
        return
    op.create_table(
        "verified_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("verification_token", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("student_no", sa.String(length=70), nullable=False),
        sa.Column("semester", sa.String(length=50), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_verified_documents_token",
        "verified_documents",
        ["verification_token"],
        unique=True,
    )
    op.create_index(
        "ix_verified_documents_institution_id",
        "verified_documents",
        ["institution_id"],
    )
    op.create_index(
        "ix_verified_documents_institution_student",
        "verified_documents",
        ["institution_id", "student_no"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "verified_documents" not in inspector.get_table_names():
        return
    op.drop_index("ix_verified_documents_institution_student", table_name="verified_documents")
    op.drop_index("ix_verified_documents_institution_id", table_name="verified_documents")
    op.drop_index("ix_verified_documents_token", table_name="verified_documents")
    op.drop_table("verified_documents")
