"""Add school_id and level to fee_installments table

Revision ID: add_school_level_to_fee_installments
Revises: acb5afbc8d7d
Create Date: 2026-04-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'add_school_level_to_fee_installments'
down_revision: Union[str, Sequence[str], None] = 'acb5afbc8d7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add school_id and level columns to fee_installments table."""
    # Add school_id column
    op.add_column('fee_installments',
        sa.Column('school_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False, server_default='1')
    )
    
    # Add level column
    op.add_column('fee_installments',
        sa.Column('level', mysql.VARCHAR(length=20), nullable=False, server_default='HND')
    )
    
    # Create indexes for the new columns
    with op.batch_alter_table('fee_installments', schema=None) as batch_op:
        batch_op.create_index('ix_fee_installment_school', ['school_id'], unique=False)
        batch_op.create_index('ix_fee_installment_school_level', ['school_id', 'level'], unique=False)


def downgrade() -> None:
    """Remove school_id and level columns from fee_installments table."""
    with op.batch_alter_table('fee_installments', schema=None) as batch_op:
        batch_op.drop_index('ix_fee_installment_school_level')
        batch_op.drop_index('ix_fee_installment_school')
    
    op.drop_column('fee_installments', 'level')
    op.drop_column('fee_installments', 'school_id')
