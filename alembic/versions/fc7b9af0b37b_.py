"""empty message

Revision ID: fc7b9af0b37b
Revises: 20260528_tenant_audit, 59808b559bf1
Create Date: 2026-05-19 16:27:30.568637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc7b9af0b37b'
down_revision: Union[str, Sequence[str], None] = ('20260528_tenant_audit', '59808b559bf1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
