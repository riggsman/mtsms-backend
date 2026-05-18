"""student_chat_messages: delivered_at + read_at (private staff receipts)

Revision ID: 20260515_chat_msg_rcpt
Revises: 20260514_stu_att_chat
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260515_chat_msg_rcpt"
down_revision: Union[str, Sequence[str], None] = "20260514_stu_att_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    if "student_chat_messages" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("student_chat_messages")}
    if "delivered_at" not in cols:
        op.add_column("student_chat_messages", sa.Column("delivered_at", sa.DateTime(), nullable=True))
    if "read_at" not in cols:
        op.add_column("student_chat_messages", sa.Column("read_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "student_chat_messages" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("student_chat_messages")}
    if "read_at" in cols:
        op.drop_column("student_chat_messages", "read_at")
    if "delivered_at" in cols:
        op.drop_column("student_chat_messages", "delivered_at")
