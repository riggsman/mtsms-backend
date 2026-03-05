"""create_email_logs_table

Revision ID: 3e1d27b53d83
Revises: 9f32521d46ef
Create Date: 2026-03-02 11:39:44.885550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e1d27b53d83'
down_revision: Union[str, Sequence[str], None] = '9f32521d46ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create email_logs table."""
    op.create_table(
        'email_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_email', sa.String(length=255), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('institution_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_logs_id'), 'email_logs', ['id'], unique=False)
    op.create_index(op.f('ix_email_logs_provider_message_id'), 'email_logs', ['provider_message_id'], unique=False)
    op.create_index(op.f('ix_email_logs_institution_id'), 'email_logs', ['institution_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Drop email_logs table."""
    op.drop_index(op.f('ix_email_logs_institution_id'), table_name='email_logs')
    op.drop_index(op.f('ix_email_logs_provider_message_id'), table_name='email_logs')
    op.drop_index(op.f('ix_email_logs_id'), table_name='email_logs')
    op.drop_table('email_logs')
