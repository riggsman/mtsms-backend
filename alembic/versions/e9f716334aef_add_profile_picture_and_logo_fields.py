"""add profile_picture and logo fields

Revision ID: e9f716334aef
Revises: a9daa934b1a5
Create Date: 2026-02-28 12:49:28.615616

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e9f716334aef'
down_revision: Union[str, Sequence[str], None] = 'a9daa934b1a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add logo column to tenant_settings table
    op.add_column('tenant_settings', sa.Column('logo', sa.String(length=500), nullable=True))
    # Add profile_picture column to users table
    op.add_column('users', sa.Column('profile_picture', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove profile_picture column from users table
    op.drop_column('users', 'profile_picture')
    # Remove logo column from tenant_settings table
    op.drop_column('tenant_settings', 'logo')
