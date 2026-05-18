"""student attendance entries + student chat threads/messages

Revision ID: 20260514_stu_att_chat
Revises: 20260514_student_rec_acad_year
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260514_stu_att_chat"
down_revision: Union[str, Sequence[str], None] = "20260514_student_rec_acad_year"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "student_attendance_entries" not in tables:
        op.create_table(
            "student_attendance_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.String(length=70), nullable=False),
            sa.Column("course_code", sa.String(length=50), nullable=False),
            sa.Column("session_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="present"),
            sa.Column("notes", sa.String(length=500), nullable=True),
            sa.Column("recorded_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_student_attendance_entries_institution_id",
            "student_attendance_entries",
            ["institution_id"],
            unique=False,
        )
        op.create_index(
            "ix_student_attendance_entries_student_id",
            "student_attendance_entries",
            ["student_id"],
            unique=False,
        )

    if "student_chat_threads" not in tables:
        op.create_table(
            "student_chat_threads",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(length=20), nullable=False),
            sa.Column("course_code", sa.String(length=50), nullable=True),
            sa.Column("student_owner_matricule", sa.String(length=70), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_student_chat_threads_institution_id",
            "student_chat_threads",
            ["institution_id"],
            unique=False,
        )
        op.create_index(
            "ix_student_chat_threads_course_code",
            "student_chat_threads",
            ["course_code"],
            unique=False,
        )
        op.create_index(
            "ix_student_chat_threads_student_owner_matricule",
            "student_chat_threads",
            ["student_owner_matricule"],
            unique=False,
        )

    if "student_chat_messages" not in tables:
        op.create_table(
            "student_chat_messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("thread_id", sa.Integer(), nullable=False),
            sa.Column("parent_message_id", sa.Integer(), nullable=True),
            sa.Column("sender_user_id", sa.Integer(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["thread_id"], ["student_chat_threads.id"]),
            sa.ForeignKeyConstraint(["parent_message_id"], ["student_chat_messages.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_student_chat_messages_thread_id",
            "student_chat_messages",
            ["thread_id"],
            unique=False,
        )
        op.create_index(
            "ix_student_chat_messages_parent_message_id",
            "student_chat_messages",
            ["parent_message_id"],
            unique=False,
        )
        op.create_index(
            "ix_student_chat_messages_sender_user_id",
            "student_chat_messages",
            ["sender_user_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    if "student_chat_messages" in tables:
        op.drop_table("student_chat_messages")
    if "student_chat_threads" in tables:
        op.drop_table("student_chat_threads")
    if "student_attendance_entries" in tables:
        op.drop_table("student_attendance_entries")
