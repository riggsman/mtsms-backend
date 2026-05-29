"""add user_push_tokens for FCM web push

Revision ID: 20260221_fcm_tokens
Revises: c123456789ab
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260221_fcm_tokens"
down_revision: Union[str, Sequence[str], None] = "c123456789ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_push_tokens" not in tables:
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

    inspector = inspect(bind)
    if "user_push_tokens" not in set(inspector.get_table_names()):
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("user_push_tokens")}
    if "ix_user_push_tokens_institution_id" not in indexes:
        op.create_index(
            "ix_user_push_tokens_institution_id",
            "user_push_tokens",
            ["institution_id"],
        )
    if "ix_user_push_tokens_user_id" not in indexes:
        op.create_index(
            "ix_user_push_tokens_user_id",
            "user_push_tokens",
            ["user_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "user_push_tokens" not in tables:
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("user_push_tokens")}
    if "ix_user_push_tokens_user_id" in indexes:
        op.drop_index("ix_user_push_tokens_user_id", table_name="user_push_tokens")
    if "ix_user_push_tokens_institution_id" in indexes:
        op.drop_index("ix_user_push_tokens_institution_id", table_name="user_push_tokens")
    op.drop_table("user_push_tokens")
