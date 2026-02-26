"""make_database_url_nullable_in_tenant

Revision ID: 7b985e8e82ab
Revises: 87ff93055548
Create Date: 2026-02-23 20:46:57.703968

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b985e8e82ab'
down_revision: Union[str, Sequence[str], None] = '87ff93055548'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Make database_url nullable in tenants table
    op.alter_column('tenants', 'database_url',
                    existing_type=sa.String(length=200),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert database_url to not nullable
    # Note: This will fail if there are NULL values, so we set a default first
    op.execute("UPDATE tenants SET database_url = '' WHERE database_url IS NULL")
    op.alter_column('tenants', 'database_url',
                    existing_type=sa.String(length=200),
                    nullable=False)
