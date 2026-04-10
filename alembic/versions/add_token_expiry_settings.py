"""add token expiry settings

Revision ID: add_token_expiry_settings
Revises: add_course_semester
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "add_token_expiry_settings"
down_revision = "add_course_semester"
branch_labels = None
depends_on = None

def _column_exists(bind, table_name, column_name) -> bool:
    insp = inspect(bind)
    if not insp.has_table(table_name):
        return False
    names = {c["name"] for c in insp.get_columns(table_name)}
    return column_name in names

def upgrade():
    bind = op.get_bind()
    if not _column_exists(bind, "system_settings", "access_token_expire_minutes"):
        op.add_column("system_settings", sa.Column("access_token_expire_minutes", sa.Integer(), nullable=False, server_default='60'))
    
    if not _column_exists(bind, "system_settings", "refresh_token_expire_days"):
        op.add_column("system_settings", sa.Column("refresh_token_expire_days", sa.Integer(), nullable=False, server_default='1'))

def downgrade():
    bind = op.get_bind()
    if _column_exists(bind, "system_settings", "refresh_token_expire_days"):
        op.drop_column("system_settings", "refresh_token_expire_days")
    if _column_exists(bind, "system_settings", "access_token_expire_minutes"):
        op.drop_column("system_settings", "access_token_expire_minutes")
