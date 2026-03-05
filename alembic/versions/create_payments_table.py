"""create payments table

Revision ID: create_payments_table
Revises: add_email_reminder_time
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'create_payments_table'
down_revision = 'add_email_reminder_time'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'payments' not in tables:
        # Create payments table
        op.create_table(
            'payments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('institution_id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('student_id_number', sa.String(length=70), nullable=False),
            sa.Column('student_name', sa.String(length=255), nullable=False),
            sa.Column('student_email', sa.String(length=255), nullable=False),
            sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='XAF'),
            sa.Column('provider', sa.String(length=20), nullable=False),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('phone_number', sa.String(length=20), nullable=False),
            sa.Column('transaction_id', sa.String(length=100), nullable=False),
            sa.Column('receipt_number', sa.String(length=100), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('payment_method', sa.String(length=50), nullable=True),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.Column('otp_sent', sa.String(length=6), nullable=True),
            sa.Column('otp_verified', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('otp_sent_at', sa.DateTime(), nullable=True),
            sa.Column('otp_verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('paid_at', sa.DateTime(), nullable=True),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
        op.create_index(op.f('ix_payments_institution_id'), 'payments', ['institution_id'], unique=False)
        op.create_index(op.f('ix_payments_student_id'), 'payments', ['student_id'], unique=False)
        op.create_index(op.f('ix_payments_student_id_number'), 'payments', ['student_id_number'], unique=False)
        op.create_index(op.f('ix_payments_student_email'), 'payments', ['student_email'], unique=False)
        op.create_index(op.f('ix_payments_transaction_id'), 'payments', ['transaction_id'], unique=True)
        op.create_index(op.f('ix_payments_receipt_number'), 'payments', ['receipt_number'], unique=True)
        op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)
        op.create_index('ix_payment_student_status', 'payments', ['student_id', 'status'], unique=False)
        op.create_index('ix_payment_institution_status', 'payments', ['institution_id', 'status'], unique=False)
        op.create_index('ix_payment_created', 'payments', ['created_at'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index('ix_payment_created', table_name='payments')
    op.drop_index('ix_payment_institution_status', table_name='payments')
    op.drop_index('ix_payment_student_status', table_name='payments')
    op.drop_index(op.f('ix_payments_status'), table_name='payments')
    op.drop_index(op.f('ix_payments_receipt_number'), table_name='payments')
    op.drop_index(op.f('ix_payments_transaction_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_student_email'), table_name='payments')
    op.drop_index(op.f('ix_payments_student_id_number'), table_name='payments')
    op.drop_index(op.f('ix_payments_student_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_institution_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    
    # Drop table
    op.drop_table('payments')
