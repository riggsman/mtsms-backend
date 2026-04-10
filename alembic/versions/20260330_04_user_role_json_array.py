"""Store users.role as JSON array of role strings.

Revision ID: 20260330_04
Revises: 20260330_03
Create Date: 2026-03-30
"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260330_04"
down_revision: Union[str, Sequence[str], None] = "20260330_03"
branch_labels = None
depends_on = None


def _parse_legacy_role(val) -> list:
    if val is None:
        return ["student"]
    if isinstance(val, (list, dict)):
        try:
            raw = json.dumps(val) if isinstance(val, dict) else val
        except Exception:
            raw = str(val)
    else:
        raw = str(val).strip()
    if not raw:
        return ["student"]
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip().lower() for x in data if x is not None and str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    out = []
    for r in parts:
        if r in {"lecturer", "teacher", "staff"}:
            r = "staff"
        if r and r not in out:
            out.append(r)
    return out if out else ["student"]


def upgrade() -> None:
    conn = op.get_bind()
    op.add_column("users", sa.Column("role_json", sa.JSON(), nullable=True))
    rows = conn.execute(sa.text("SELECT id, role FROM users")).fetchall()
    for uid, role_val in rows:
        arr = _parse_legacy_role(role_val)
        conn.execute(
            sa.text("UPDATE users SET role_json = :j WHERE id = :id"),
            {"j": json.dumps(arr), "id": uid},
        )
    op.drop_column("users", "role")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role_json",
            new_column_name="role",
            existing_type=sa.JSON(),
            nullable=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    op.add_column("users", sa.Column("role_str", sa.String(70), nullable=True))
    rows = conn.execute(sa.text("SELECT id, role FROM users")).fetchall()
    for uid, role_val in rows:
        if isinstance(role_val, list):
            s = ",".join(sorted({str(x).strip().lower() for x in role_val if x}))
        elif role_val is None:
            s = "student"
        else:
            try:
                data = json.loads(str(role_val))
                if isinstance(data, list):
                    s = ",".join(sorted(str(x).strip().lower() for x in data if x))
                else:
                    s = str(role_val)
            except (json.JSONDecodeError, TypeError):
                s = str(role_val)
        if not s:
            s = "student"
        conn.execute(
            sa.text("UPDATE users SET role_str = :r WHERE id = :id"),
            {"r": s, "id": uid},
        )
    op.drop_column("users", "role")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role_str",
            new_column_name="role",
            existing_type=sa.String(70),
            nullable=False,
        )
