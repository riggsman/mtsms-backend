"""Seed default system superadmin user (idempotent).

Revision ID: 20260529_seed_superadmin
Revises: fc7b9af0b37b
Create Date: 2026-05-29

Default credentials after upgrade:
  username: superadmin
  password: superadmin
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_seed_superadmin"
down_revision: Union[str, Sequence[str], None] = "fc7b9af0b37b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_EMAIL = "support@riggsmantechnologies.com"
DEFAULT_USERNAME = "superadmin"
DEFAULT_PASSWORD_PLAIN = "superadmin"


def _user_exists(conn) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT id FROM users "
            "WHERE email = :email OR username = :username "
            "LIMIT 1"
        ),
        {"email": DEFAULT_EMAIL, "username": DEFAULT_USERNAME},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    conn = bind
    if _user_exists(conn):
        return

    from app.authentication.authenticator import hash_password

    now = datetime.utcnow()
    users = sa.table(
        "users",
        sa.column("institution_id", sa.Integer()),
        sa.column("branch_id", sa.Integer()),
        sa.column("department_id", sa.Integer()),
        sa.column("position", sa.String(length=120)),
        sa.column("firstname", sa.String(length=70)),
        sa.column("middlename", sa.String(length=200)),
        sa.column("lastname", sa.String(length=70)),
        sa.column("gender", sa.String(length=70)),
        sa.column("address", sa.String(length=200)),
        sa.column("email", sa.String(length=70)),
        sa.column("phone", sa.String(length=200)),
        sa.column("username", sa.String(length=50)),
        sa.column("password", sa.String(length=200)),
        sa.column("role", sa.JSON()),
        sa.column("system_permissions", sa.JSON()),
        sa.column("user_type", sa.String(length=20)),
        sa.column("is_active", sa.String(length=10)),
        sa.column("must_change_password", sa.String(length=10)),
        sa.column("profile_picture", sa.String(length=500)),
        sa.column("language", sa.String(length=8)),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )

    conn.execute(
        users.insert().values(
            institution_id=None,
            branch_id=None,
            department_id=None,
            position=None,
            firstname="System",
            middlename=None,
            lastname="SuperAdmin",
            gender="male",
            address="System",
            email=DEFAULT_EMAIL,
            phone="+0000000000",
            username=DEFAULT_USERNAME,
            password=hash_password(DEFAULT_PASSWORD_PLAIN),
            role=["system_super_admin"],
            system_permissions=None,
            user_type="SYSTEM",
            is_active="active",
            must_change_password="false",
            profile_picture=None,
            language="en",
            created_at=now,
            updated_at=None,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    bind.execute(
        sa.text(
            "DELETE FROM users "
            "WHERE email = :email OR username = :username"
        ),
        {"email": DEFAULT_EMAIL, "username": DEFAULT_USERNAME},
    )
