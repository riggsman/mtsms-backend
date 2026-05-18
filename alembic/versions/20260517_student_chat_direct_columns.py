"""student_chat_threads: directed staff + peer direct messaging columns

Revision ID: 20260517_stu_chat_dm
Revises: 20260516_login_email_otp
Create Date: 2026-05-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260517_stu_chat_dm"
down_revision: Union[str, Sequence[str], None] = "20260516_login_email_otp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "student_chat_threads" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("student_chat_threads")}
    if "direct_peer_matricule" not in cols:
        op.add_column(
            "student_chat_threads",
            sa.Column("direct_peer_matricule", sa.String(length=70), nullable=True),
        )
        op.create_index(
            "ix_student_chat_threads_direct_peer_matricule",
            "student_chat_threads",
            ["direct_peer_matricule"],
            unique=False,
        )
    if "counterpart_user_id" not in cols:
        op.add_column(
            "student_chat_threads",
            sa.Column("counterpart_user_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            "ix_student_chat_threads_counterpart_user_id",
            "student_chat_threads",
            ["counterpart_user_id"],
            unique=False,
        )
        insp2 = inspect(bind)
        fk_names = [fk["name"] for fk in insp2.get_foreign_keys("student_chat_threads")]
        if "student_chat_threads_counterpart_user_id_fkey" not in fk_names:
            op.create_foreign_key(
                "student_chat_threads_counterpart_user_id_fkey",
                "student_chat_threads",
                "users",
                ["counterpart_user_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "student_chat_threads" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("student_chat_threads")}
    if "counterpart_user_id" in cols:
        try:
            op.drop_constraint("student_chat_threads_counterpart_user_id_fkey", "student_chat_threads", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index("ix_student_chat_threads_counterpart_user_id", table_name="student_chat_threads")
        except Exception:
            pass
        op.drop_column("student_chat_threads", "counterpart_user_id")
    if "direct_peer_matricule" in cols:
        try:
            op.drop_index("ix_student_chat_threads_direct_peer_matricule", table_name="student_chat_threads")
        except Exception:
            pass
        op.drop_column("student_chat_threads", "direct_peer_matricule")
