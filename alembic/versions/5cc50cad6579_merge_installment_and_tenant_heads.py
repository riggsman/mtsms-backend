"""merge_installment_and_tenant_heads

Revision ID: 5cc50cad6579
Revises: add_school_level_to_fee_installments, d4d8d7c8884b
Create Date: 2026-04-11 02:51:48.365373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5cc50cad6579'
down_revision: Union[str, Sequence[str], None] = ('add_school_level_to_fee_installments', 'd4d8d7c8884b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
