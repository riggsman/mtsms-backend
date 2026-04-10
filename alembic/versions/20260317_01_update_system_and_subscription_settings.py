"""add cache/timeout and subscription flags

Revision ID: 20260317_01
Revises: 7edf0a51b08d
Create Date: 2026-03-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260317_01"
down_revision: Union[str, Sequence[str], None] = "7edf0a51b08d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new settings columns and subscription flags."""
    # --- system_settings additions ---
    with op.batch_alter_table("system_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "cache_timeout",
                sa.Integer(),
                nullable=False,
                server_default="5",
            )
        )
        batch_op.add_column(
            sa.Column(
                "inactivity_timeout",
                sa.Integer(),
                nullable=False,
                server_default="5",
            )
        )
        batch_op.add_column(
            sa.Column(
                "maintenance_check_interval",
                sa.Integer(),
                nullable=False,
                server_default="60",
            )
        )

    # Remove server_default after data is populated so future inserts
    # rely on application-level defaults.
    with op.batch_alter_table("system_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "cache_timeout",
            server_default=None,
        )
        batch_op.alter_column(
            "inactivity_timeout",
            server_default=None,
        )
        batch_op.alter_column(
            "maintenance_check_interval",
            server_default=None,
        )

    # --- subscription_services additions ---
    with op.batch_alter_table("subscription_services", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_freemium_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_premium_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # Clear server_default so ORM uses model defaults going forward
    with op.batch_alter_table("subscription_services", schema=None) as batch_op:
        batch_op.alter_column(
            "is_freemium_enabled",
            server_default=None,
        )
        batch_op.alter_column(
            "is_premium_enabled",
            server_default=None,
        )


def downgrade() -> None:
    """Revert new settings columns and subscription flags."""
    with op.batch_alter_table("subscription_services", schema=None) as batch_op:
        batch_op.drop_column("is_premium_enabled")
        batch_op.drop_column("is_freemium_enabled")

    with op.batch_alter_table("system_settings", schema=None) as batch_op:
        batch_op.drop_column("maintenance_check_interval")
        batch_op.drop_column("inactivity_timeout")
        batch_op.drop_column("cache_timeout")

