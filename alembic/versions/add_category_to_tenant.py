"""add_category_to_tenant

Revision ID: add_category_to_tenant
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_category_to_tenant'
down_revision: Union[str, Sequence[str], None] = '27debf04606e'  # Latest migration: add_firebase_messaging_table
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category column to tenants table."""
    # Add category column - nullable initially to handle existing tenants
    op.add_column('tenants', sa.Column('category', sa.String(length=10), nullable=True))
    
    # Set default value for existing tenants (you can change 'HI' to your preferred default)
    op.execute("UPDATE tenants SET category = 'HI' WHERE category IS NULL")
    
    # Make the column non-nullable after setting defaults
    op.alter_column('tenants', 'category',
                    existing_type=sa.String(length=10),
                    nullable=False)


def downgrade() -> None:
    """Remove category column from tenants table."""
    op.drop_column('tenants', 'category')
