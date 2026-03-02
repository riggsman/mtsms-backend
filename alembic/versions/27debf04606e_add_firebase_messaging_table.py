"""Add firebase messaging table

Revision ID: 27debf04606e
Revises: 1a95d556fa89
Create Date: 2026-02-27 13:35:32.438561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27debf04606e'
down_revision: Union[str, Sequence[str], None] = '1a95d556fa89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
