"""Add academic_year_id to school_fees for per-year program fees."""
from alembic import op
import sqlalchemy as sa

revision = "20260524_school_fees_ay"
down_revision = "20260523_platform_errors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "school_fees" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("school_fees")}
    if "academic_year_id" not in cols:
        op.add_column(
            "school_fees",
            sa.Column("academic_year_id", sa.Integer(), nullable=True),
        )
    indexes = {idx["name"] for idx in inspector.get_indexes("school_fees")}
    if "ix_school_fees_academic_year_id" not in indexes:
        op.create_index(
            "ix_school_fees_academic_year_id",
            "school_fees",
            ["academic_year_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "school_fees" not in inspector.get_table_names():
        return
    indexes = {idx["name"] for idx in inspector.get_indexes("school_fees")}
    if "ix_school_fees_academic_year_id" in indexes:
        op.drop_index("ix_school_fees_academic_year_id", table_name="school_fees")
    cols = {c["name"] for c in inspector.get_columns("school_fees")}
    if "academic_year_id" in cols:
        op.drop_column("school_fees", "academic_year_id")
