"""merge multiple heads

Revision ID: d4fe0ebb476c
Revises: 037bdabd9193, add_token_expiry_settings
Create Date: 2026-04-09 14:55:03.070449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4fe0ebb476c'
down_revision: Union[str, Sequence[str], None] = ('037bdabd9193', 'add_token_expiry_settings')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
