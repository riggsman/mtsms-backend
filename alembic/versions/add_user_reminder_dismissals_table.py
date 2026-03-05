"""add user reminder dismissals table

Revision ID: add_user_reminder_dismissals
Revises: add_schedule_reminders
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_reminder_dismissals'
down_revision = 'add_schedule_reminders'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'user_reminder_dismissals' not in tables:
        # Create user_reminder_dismissals table
        op.create_table(
            'user_reminder_dismissals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('reminder_id', sa.Integer(), nullable=False),
            sa.Column('dismissed_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['reminder_id'], ['schedule_reminders.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('ix_user_reminder_dismissals_user_id', 'user_reminder_dismissals', ['user_id'])
        op.create_index('ix_user_reminder_dismissals_reminder_id', 'user_reminder_dismissals', ['reminder_id'])
        
        # Create unique composite index to prevent duplicate dismissals
        op.create_index(
            'ix_user_reminder_dismissal_unique',
            'user_reminder_dismissals',
            ['user_id', 'reminder_id'],
            unique=True
        )


def downgrade():
    # Drop indexes
    op.drop_index('ix_user_reminder_dismissal_unique', table_name='user_reminder_dismissals')
    op.drop_index('ix_user_reminder_dismissals_reminder_id', table_name='user_reminder_dismissals')
    op.drop_index('ix_user_reminder_dismissals_user_id', table_name='user_reminder_dismissals')
    
    # Drop table
    op.drop_table('user_reminder_dismissals')
