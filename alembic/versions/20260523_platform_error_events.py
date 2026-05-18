"""platform_error_events for unified error analytics

Revision ID: 20260523_platform_errors
Revises: 20260522_platform_analytics
Create Date: 2026-05-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260523_platform_errors"
down_revision: Union[str, Sequence[str], None] = "20260522_platform_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "platform_error_events" in insp.get_table_names():
        return
    op.create_table(
        "platform_error_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("tenant_name", sa.String(70), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("error_type", sa.String(64), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("method", sa.String(10), nullable=True),
        sa.Column("path", sa.String(512), nullable=True),
        sa.Column("route_template", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_platform_error_tenant_created",
        "platform_error_events",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_platform_error_source_type",
        "platform_error_events",
        ["source", "error_type"],
    )


def downgrade() -> None:
    op.drop_table("platform_error_events")
