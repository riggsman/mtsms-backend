"""updated tenant id to be a foreign key in specialty table to track student speicialties

Revision ID: d4d8d7c8884b
Revises: 968013298ebd
Create Date: 2026-04-10 15:08:09.809794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd4d8d7c8884b'
down_revision: Union[str, Sequence[str], None] = '968013298ebd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # These tables were already dropped or handled in previous migrations.
    # The goal is to add a foreign key to institution_id in specializations table.
    with op.batch_alter_table('specializations', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'specializations_institution_fk',
            'tenants',
            ['institution_id'],
            ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('specializations', schema=None) as batch_op:
        batch_op.drop_constraint('specializations_institution_fk', type_='foreignkey')
