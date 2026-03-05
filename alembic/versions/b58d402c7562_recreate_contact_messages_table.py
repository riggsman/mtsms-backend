"""recreate contact messages table

Revision ID: b58d402c7562
Revises: a47c301b6451
Create Date: 2026-03-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'b58d402c7562'
down_revision: Union[str, Sequence[str], None] = 'a47c301b6451'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate tables that were accidentally dropped but are still needed by the codebase."""
    
    # Recreate subscription_services table
    op.create_table('subscription_services',
        sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
        sa.Column('name', mysql.VARCHAR(length=200), nullable=False),
        sa.Column('description', mysql.TEXT(), nullable=True),
        sa.Column('price', mysql.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('currency', mysql.VARCHAR(length=10), nullable=False),
        sa.Column('billing_period', mysql.VARCHAR(length=50), nullable=False),
        sa.Column('is_active', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('features', mysql.TEXT(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(), nullable=False),
        sa.Column('updated_at', mysql.DATETIME(), nullable=True),
        sa.Column('deleted_at', mysql.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='latin1',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_subscription_services_name'), 'subscription_services', ['name'], unique=True)
    op.create_index(op.f('ix_subscription_services_id'), 'subscription_services', ['id'], unique=False)
    
    # Recreate service_configurations table (with foreign key constraint)
    op.create_table('service_configurations',
        sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
        sa.Column('service_name', mysql.VARCHAR(length=200), nullable=False),
        sa.Column('configuration_key', mysql.VARCHAR(length=200), nullable=False),
        sa.Column('configuration_value', mysql.TEXT(), nullable=True),
        sa.Column('description', mysql.TEXT(), nullable=True),
        sa.Column('is_active', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('tenant_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
        sa.Column('created_at', mysql.DATETIME(), nullable=False),
        sa.Column('updated_at', mysql.DATETIME(), nullable=True),
        sa.Column('deleted_at', mysql.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('service_configurations_ibfk_1')),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='latin1',
        mysql_engine='InnoDB'
    )
    # Create index AFTER table creation (index will be created automatically by ForeignKey, but we create explicit index too)
    op.create_index(op.f('ix_service_configurations_tenant_id'), 'service_configurations', ['tenant_id'], unique=False)
    
    # Recreate contact_messages table
    op.create_table('contact_messages',
        sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
        sa.Column('institution_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
        sa.Column('name', mysql.VARCHAR(length=200), nullable=False),
        sa.Column('email', mysql.VARCHAR(length=200), nullable=False),
        sa.Column('subject', mysql.VARCHAR(length=200), nullable=False),
        sa.Column('message', mysql.TEXT(), nullable=False),
        sa.Column('phone', mysql.VARCHAR(length=100), nullable=True),
        sa.Column('is_read', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('reply_subject', mysql.VARCHAR(length=200), nullable=True),
        sa.Column('reply_message', mysql.TEXT(), nullable=True),
        sa.Column('replied_at', mysql.DATETIME(), nullable=True),
        sa.Column('replied_by', mysql.VARCHAR(length=200), nullable=True),
        sa.Column('replied_by_role', mysql.VARCHAR(length=100), nullable=True),
        sa.Column('created_at', mysql.DATETIME(), nullable=False),
        sa.Column('updated_at', mysql.DATETIME(), nullable=True),
        sa.Column('deleted_at', mysql.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='latin1',
        mysql_engine='InnoDB'
    )
    # Create indexes
    op.create_index(op.f('ix_contact_messages_id'), 'contact_messages', ['id'], unique=False)
    op.create_index(op.f('ix_contact_messages_email'), 'contact_messages', ['email'], unique=False)
    op.create_index(op.f('ix_contact_messages_institution_id'), 'contact_messages', ['institution_id'], unique=False)
    
    # Recreate system_settings table
    op.create_table('system_settings',
        sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
        sa.Column('maintenance_mode', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('allow_new_registrations', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('max_tenants', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
        sa.Column('session_timeout', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
        sa.Column('email_notifications', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('firebase_messaging_enabled', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False),
        sa.Column('firebase_api_key', mysql.VARCHAR(length=500), nullable=True),
        sa.Column('firebase_auth_domain', mysql.VARCHAR(length=255), nullable=True),
        sa.Column('firebase_project_id', mysql.VARCHAR(length=255), nullable=True),
        sa.Column('firebase_messaging_sender_id', mysql.VARCHAR(length=255), nullable=True),
        sa.Column('firebase_app_id', mysql.VARCHAR(length=255), nullable=True),
        sa.Column('firebase_vapid_key', mysql.VARCHAR(length=500), nullable=True),
        sa.Column('created_at', mysql.DATETIME(), nullable=False),
        sa.Column('updated_at', mysql.DATETIME(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_default_charset='latin1',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)


def downgrade() -> None:
    """Drop recreated tables."""
    # Drop system_settings
    op.drop_index(op.f('ix_system_settings_id'), table_name='system_settings')
    op.drop_table('system_settings')
    
    # Drop contact_messages
    op.drop_index(op.f('ix_contact_messages_institution_id'), table_name='contact_messages')
    op.drop_index(op.f('ix_contact_messages_email'), table_name='contact_messages')
    op.drop_index(op.f('ix_contact_messages_id'), table_name='contact_messages')
    op.drop_table('contact_messages')
    
    # Drop service_configurations (drop FK constraint first, then index, then table)
    op.drop_constraint('service_configurations_ibfk_1', 'service_configurations', type_='foreignkey')
    op.drop_index(op.f('ix_service_configurations_tenant_id'), table_name='service_configurations')
    op.drop_table('service_configurations')
    
    # Drop subscription_services
    op.drop_index(op.f('ix_subscription_services_id'), table_name='subscription_services')
    op.drop_index(op.f('ix_subscription_services_name'), table_name='subscription_services')
    op.drop_table('subscription_services')
