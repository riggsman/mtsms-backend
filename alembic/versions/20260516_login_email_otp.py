"""login_email_otps for passwordless email OTP login

Revision ID: 20260516_login_email_otp
Revises: 20260515_chat_msg_rcpt
Create Date: 2026-05-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_login_email_otp"
down_revision: Union[str, Sequence[str], None] = "20260515_chat_msg_rcpt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_email_otps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(200), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_login_email_otps_user_id", "login_email_otps", ["user_id"])
    op.create_index("ix_login_email_otps_expires_at", "login_email_otps", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_login_email_otps_expires_at", table_name="login_email_otps")
    op.drop_index("ix_login_email_otps_user_id", table_name="login_email_otps")
    op.drop_table("login_email_otps")
