"""add logo_url to tenant table

Revision ID: add_logo_url_tenant
Revises: e9f716334aef
Create Date: 2026-02-28 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ff4fe6f7a44'
down_revision: Union[str, Sequence[str], None] = 'e9f716334aef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add logo_url column to tenants table
    op.add_column('tenants', sa.Column('logo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove logo_url column from tenants table
    op.drop_column('tenants', 'logo_url')
