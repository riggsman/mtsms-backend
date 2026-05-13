"""add user_push_tokens for FCM web push

Revision ID: 20260221_fcm_tokens
Revises: c123456789ab
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260221_fcm_tokens"
down_revision: Union[str, Sequence[str], None] = "c123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_push_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_push_tokens_institution_id", "user_push_tokens", ["institution_id"])
    op.create_index("ix_user_push_tokens_user_id", "user_push_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_push_tokens_user_id", table_name="user_push_tokens")
    op.drop_index("ix_user_push_tokens_institution_id", table_name="user_push_tokens")
    op.drop_table("user_push_tokens")
