"""empty message

Revision ID: ff546592286b
Revises: 7b985e8e82ab, f1a2b3c4d5e6
Create Date: 2026-02-24 12:30:46.473069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff546592286b'
down_revision: Union[str, Sequence[str], None] = ('7b985e8e82ab', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
