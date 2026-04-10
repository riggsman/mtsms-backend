"""add semester to courses

Revision ID: add_course_semester
Revises: 7269ec9de6e1
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "add_course_semester"
down_revision = "7269ec9de6e1"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_courses_semester"

def _courses_semester_exists(bind) -> bool:
    insp = inspect(bind)
    if not insp.has_table("courses"):
        return False
    names = {c["name"] for c in insp.get_columns("courses")}
    return "semester" in names

def _index_exists(bind, table: str, index_name: str) -> bool:
    insp = inspect(bind)
    want = index_name.lower()
    for ix in insp.get_indexes(table):
        name = ix.get("name") or ""
        if name.lower() == want:
            return True
    return False

def upgrade():
    # Matches app.models.course.Course.semester (SmallInteger).
    # Idempotent: safe if column/index already present (e.g. manual ALTER or wrong DB retried).
    bind = op.get_bind()
    if not _courses_semester_exists(bind):
        op.add_column(
            "courses",
            sa.Column("semester", sa.SmallInteger(), nullable=True),
        )
    if not _index_exists(bind, "courses", INDEX_NAME):
        op.create_index(INDEX_NAME, "courses", ["semester"], unique=False)

def downgrade():
    bind = op.get_bind()
    if _index_exists(bind, "courses", INDEX_NAME):
        op.drop_index(INDEX_NAME, table_name="courses")
    if _courses_semester_exists(bind):
        op.drop_column("courses", "semester")
