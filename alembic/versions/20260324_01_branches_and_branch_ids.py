"""branches table and branch_id on users, students, teachers; branches_enabled on tenant_settings

Revision ID: 20260324_01
Revises: 20260317_01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260324_01"
down_revision: Union[str, Sequence[str], None] = "20260317_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_branches_institution_id", "branches", ["institution_id"])

    with op.batch_alter_table("tenant_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "branches_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    with op.batch_alter_table("tenant_settings", schema=None) as batch_op:
        batch_op.alter_column("branches_enabled", server_default=None)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True)
        )
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True)
        )
    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.drop_column("branch_id")
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_column("branch_id")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("branch_id")
    with op.batch_alter_table("tenant_settings", schema=None) as batch_op:
        batch_op.drop_column("branches_enabled")
    op.drop_index("ix_branches_institution_id", table_name="branches")
    op.drop_table("branches")
