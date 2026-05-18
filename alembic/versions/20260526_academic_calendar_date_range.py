"""Add event_end_date to academic_calendar for date ranges."""
from alembic import op
import sqlalchemy as sa

revision = "20260526_cal_date_range"
down_revision = "20260525_academic_calendar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "academic_calendar" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("academic_calendar")}
    if "event_end_date" not in cols:
        op.add_column("academic_calendar", sa.Column("event_end_date", sa.Date(), nullable=True))
        op.execute("UPDATE academic_calendar SET event_end_date = event_date WHERE event_end_date IS NULL")
        op.alter_column(
            "academic_calendar",
            "event_end_date",
            existing_type=sa.Date(),
            nullable=False,
        )
    else:
        op.execute(
            "UPDATE academic_calendar SET event_end_date = event_date "
            "WHERE event_end_date IS NULL"
        )

    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("academic_calendar")}
    if "uq_academic_calendar_inst_year_date" in indexes:
        op.drop_index("uq_academic_calendar_inst_year_date", table_name="academic_calendar")
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("academic_calendar")}
    if "uq_academic_calendar_inst_year_date_range" not in indexes:
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

    indexes = {idx["name"] for idx in inspector.get_indexes("academic_calendar")}
    if "uq_academic_calendar_inst_year_date_range" in indexes:
        op.drop_index("uq_academic_calendar_inst_year_date_range", table_name="academic_calendar")
    if "uq_academic_calendar_inst_year_date" not in indexes:
        op.create_index(
            "uq_academic_calendar_inst_year_date",
            "academic_calendar",
            ["institution_id", "academic_year_id", "event_date"],
            unique=True,
        )

    cols = {c["name"] for c in inspector.get_columns("academic_calendar")}
    if "event_end_date" in cols:
        op.drop_column("academic_calendar", "event_end_date")
