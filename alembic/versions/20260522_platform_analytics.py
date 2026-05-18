"""Platform analytics tables (login, OTP, email, API request logs)

Revision ID: 20260522_platform_analytics
Revises: 20260521_tenant_features
Create Date: 2026-05-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260522_platform_analytics"
down_revision: Union[str, Sequence[str], None] = "20260521_tenant_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = set(insp.get_table_names())

    if "login_audit_events" not in existing:
        op.create_table(
            "login_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("tenant_name", sa.String(70), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("identifier", sa.String(255), nullable=True),
            sa.Column("method", sa.String(32), nullable=False),
            sa.Column("outcome", sa.String(16), nullable=False),
            sa.Column("failure_reason", sa.String(64), nullable=True),
            sa.Column("failure_detail", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_login_audit_tenant_created", "login_audit_events", ["tenant_id", "created_at"])
        op.create_index("ix_login_audit_outcome", "login_audit_events", ["outcome", "failure_reason"])

    if "otp_audit_events" not in existing:
        op.create_table(
            "otp_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("tenant_name", sa.String(70), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(32), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_otp_audit_tenant_created", "otp_audit_events", ["tenant_id", "created_at"])

    if "platform_email_events" not in existing:
        op.create_table(
            "platform_email_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("recipient_email", sa.String(255), nullable=False),
            sa.Column("subject", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("email_category", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_platform_email_tenant_created", "platform_email_events", ["tenant_id", "created_at"])

    if "api_request_logs" not in existing:
        op.create_table(
            "api_request_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("tenant_name", sa.String(70), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("method", sa.String(10), nullable=False),
            sa.Column("path", sa.String(512), nullable=False),
            sa.Column("route_template", sa.String(512), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("billing_category", sa.String(32), nullable=False, server_default="api"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_api_request_tenant_created", "api_request_logs", ["tenant_id", "created_at"])
        op.create_index("ix_api_request_route", "api_request_logs", ["route_template"])


def downgrade() -> None:
    op.drop_table("api_request_logs")
    op.drop_table("platform_email_events")
    op.drop_table("otp_audit_events")
    op.drop_table("login_audit_events")
