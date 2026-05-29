"""empty message

Revision ID: 9bacb06b09f8
Revises: 20260532_tenant_prog_levels
Create Date: 2026-05-27 01:28:24.606679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bacb06b09f8'
down_revision: Union[str, Sequence[str], None] = '20260532_tenant_prog_levels'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
