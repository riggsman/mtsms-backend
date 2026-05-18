"""Add academic_calendar table for tenant academic year activities."""
from alembic import op
import sqlalchemy as sa

revision = "20260525_academic_calendar"
down_revision = "20260524_school_fees_ay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "academic_calendar" in inspector.get_table_names():
        return
    op.create_table(
        "academic_calendar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_end_date", sa.Date(), nullable=False),
        sa.Column("activity", sa.Text(), nullable=False),
        sa.Column("row_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_academic_calendar_institution_id",
        "academic_calendar",
        ["institution_id"],
    )
    op.create_index(
        "ix_academic_calendar_academic_year_id",
        "academic_calendar",
        ["academic_year_id"],
    )
    op.create_index(
        "uq_academic_calendar_inst_year_date_range",
        "academic_calendar",
        ["institution_id", "academic_year_id", "event_date", "event_end_date"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "academic_calendar" not in inspector.get_table_names():
        return
    op.drop_index("uq_academic_calendar_inst_year_date_range", table_name="academic_calendar")
    op.drop_index("ix_academic_calendar_academic_year_id", table_name="academic_calendar")
    op.drop_index("ix_academic_calendar_institution_id", table_name="academic_calendar")
    op.drop_table("academic_calendar")
