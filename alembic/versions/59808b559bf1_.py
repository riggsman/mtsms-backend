"""empty message

Revision ID: 59808b559bf1
Revises: 20260527_tenant_services, 982059817002
Create Date: 2026-05-19 14:00:22.187151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59808b559bf1'
down_revision: Union[str, Sequence[str], None] = ('20260527_tenant_services', '982059817002')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
