"""Repair missing branch columns (shared schema)

The app models expect:
- users.branch_id (FK -> branches.id)
- students.branch_id (FK -> branches.id)
- teachers.branch_id (FK -> branches.id)
- tenant_settings.branches_enabled (NOT NULL)

Some environments show these columns missing even though alembic_version
was advanced. This migration brings the shared schema back in sync.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "repair_missing_branch_columns"
down_revision: Union[str, Sequence[str], None] = "fcaca6ae897b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("branch_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, "branches", ["branch_id"], ["id"])

    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(sa.Column("branch_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, "branches", ["branch_id"], ["id"])

    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("branch_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, "branches", ["branch_id"], ["id"])

    with op.batch_alter_table("tenant_settings", schema=None) as batch_op:
        # server_default ensures existing rows get a value.
        batch_op.add_column(
            sa.Column(
                "branches_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    # Drop in reverse order. Note: dropping FKs first is important.
    with op.batch_alter_table("tenant_settings", schema=None) as batch_op:
        batch_op.drop_column("branches_enabled")

    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("branch_id")

    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("branch_id")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("branch_id")

