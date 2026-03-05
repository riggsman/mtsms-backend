"""add email_reminder_time to tenant_settings

Revision ID: add_email_reminder_time
Revises: add_user_reminder_dismissals
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_email_reminder_time'
down_revision = 'add_user_reminder_dismissals'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get columns for tenant_settings table
    columns = [col['name'] for col in inspector.get_columns('tenant_settings')]
    
    if 'email_reminder_time' not in columns:
        # Add email_reminder_time column to tenant_settings table
        op.add_column(
            'tenant_settings',
            sa.Column('email_reminder_time', sa.Integer(), nullable=True, server_default='30')
        )
        
        # Update existing rows to have default value
        conn.execute(text("UPDATE tenant_settings SET email_reminder_time = 30 WHERE email_reminder_time IS NULL"))


def downgrade():
    # Remove email_reminder_time column
    op.drop_column('tenant_settings', 'email_reminder_time')
