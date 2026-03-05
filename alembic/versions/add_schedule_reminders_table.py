"""add schedule reminders table

Revision ID: add_schedule_reminders
Revises: 4fbac6da3d45
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_schedule_reminders'
down_revision = '4fbac6da3d45'  # Update this with your latest migration revision
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'schedule_reminders' not in tables:
        # Create schedule_reminders table
        op.create_table(
            'schedule_reminders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('schedule_id', sa.Integer(), nullable=False),
            sa.Column('institution_id', sa.Integer(), nullable=False),
            sa.Column('reminder_type', sa.String(length=20), nullable=False),
            sa.Column('recipient_email', sa.String(length=255), nullable=False),
            sa.Column('reminder_time', sa.DateTime(), nullable=False),
            sa.Column('class_start_time', sa.DateTime(), nullable=False),
            sa.Column('sent_at', sa.DateTime(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('error_message', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('ix_schedule_reminders_schedule_id', 'schedule_reminders', ['schedule_id'])
        op.create_index('ix_schedule_reminders_institution_id', 'schedule_reminders', ['institution_id'])
        op.create_index('ix_schedule_reminders_recipient_email', 'schedule_reminders', ['recipient_email'])
        
        # Create unique composite index to prevent duplicate reminders
        op.create_index(
            'ix_schedule_reminder_unique',
            'schedule_reminders',
            ['schedule_id', 'reminder_type', 'recipient_email', 'class_start_time'],
            unique=True
        )
    else:
        # Table exists, check if indexes exist and create them if missing
        indexes = [idx['name'] for idx in inspector.get_indexes('schedule_reminders')]
        if 'ix_schedule_reminders_schedule_id' not in indexes:
            op.create_index('ix_schedule_reminders_schedule_id', 'schedule_reminders', ['schedule_id'])
        if 'ix_schedule_reminders_institution_id' not in indexes:
            op.create_index('ix_schedule_reminders_institution_id', 'schedule_reminders', ['institution_id'])
        if 'ix_schedule_reminders_recipient_email' not in indexes:
            op.create_index('ix_schedule_reminders_recipient_email', 'schedule_reminders', ['recipient_email'])
        if 'ix_schedule_reminder_unique' not in indexes:
            try:
                op.create_index(
                    'ix_schedule_reminder_unique',
                    'schedule_reminders',
                    ['schedule_id', 'reminder_type', 'recipient_email', 'class_start_time'],
                    unique=True
                )
            except Exception:
                pass  # Index might already exist


def downgrade():
    # Drop indexes
    op.drop_index('ix_schedule_reminder_unique', table_name='schedule_reminders')
    op.drop_index('ix_schedule_reminders_recipient_email', table_name='schedule_reminders')
    op.drop_index('ix_schedule_reminders_institution_id', table_name='schedule_reminders')
    op.drop_index('ix_schedule_reminders_schedule_id', table_name='schedule_reminders')
    
    # Drop table
    op.drop_table('schedule_reminders')
