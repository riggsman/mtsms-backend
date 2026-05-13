"""users: optional JSON permissions for SYSTEM users (e.g. database_config)

Revision ID: 20260502_system_permissions
Revises: 20260501_payroll_code_used
Create Date: 2026-05-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260502_system_permissions"
down_revision: Union[str, Sequence[str], None] = "20260501_payroll_code_used"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("system_permissions", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "system_permissions")
