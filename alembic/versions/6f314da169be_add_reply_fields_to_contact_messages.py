"""Add reply fields to contact_messages

Revision ID: 6f314da169be
Revises: 76ec4727ee71
Create Date: 2026-02-27 12:20:21.004637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f314da169be'
down_revision: Union[str, Sequence[str], None] = '76ec4727ee71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
