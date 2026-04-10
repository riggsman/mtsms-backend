"""merge divergent migration branches

Revision ID: 7269ec9de6e1
Revises: 20260330_04, repair_missing_branch_columns
Create Date: 2026-04-02 00:45:00.055694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7269ec9de6e1'
down_revision: Union[str, Sequence[str], None] = ('20260330_04', 'repair_missing_branch_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
