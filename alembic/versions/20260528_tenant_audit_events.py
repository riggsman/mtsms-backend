"""tenant_audit_events table for suspend/resume audit trail."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260528_tenant_audit"
down_revision: Union[str, Sequence[str], None] = "20260527_tenant_services"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "tenant_audit_events" in insp.get_table_names():
        return
    op.create_table(
        "tenant_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_audit_tenant_id", "tenant_audit_events", ["tenant_id"])
    op.create_index("ix_tenant_audit_action", "tenant_audit_events", ["action"])
    op.create_index("ix_tenant_audit_actor", "tenant_audit_events", ["actor_user_id"])
    op.create_index("ix_tenant_audit_created", "tenant_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("tenant_audit_events")
