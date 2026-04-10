"""Replace lecturer role values with staff in users.role.

Revision ID: 20260330_03
Revises: 20260330_02
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260330_03"
down_revision: Union[str, Sequence[str], None] = "20260330_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Replace lecturer token in comma-separated roles (MySQL/SQLite compatible)
    conn.execute(sa.text("UPDATE users SET role = REPLACE(role, 'lecturer', 'staff') WHERE role IS NOT NULL AND role LIKE '%lecturer%'"))


def downgrade() -> None:
    # Irreversible: cannot safely map staff back to lecturer without losing other staff users.
    pass
