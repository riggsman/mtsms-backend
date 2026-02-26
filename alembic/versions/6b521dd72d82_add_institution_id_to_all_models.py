"""add_institution_id_to_all_models

Revision ID: 6b521dd72d82
Revises: 8e74aa2196f1
Create Date: 2026-02-23 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b521dd72d82'
down_revision: Union[str, Sequence[str], None] = '8e74aa2196f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add institution_id column to all tenant-specific models."""
    # List of tables that need institution_id
    tables = [
        'students',
        'teachers',
        'courses',
        'schedules',
        'student_records',
        'complaints',
        'assignments',
        'assignment_submissions',
        'enrollments',
        'departments',
        'classes',
        'academic_years',
        'guardians'
    ]
    
    for table in tables:
        try:
            # Check if column already exists
            connection = op.get_bind()
            inspector = sa.inspect(connection)
            columns = [col['name'] for col in inspector.get_columns(table)]
            
            if 'institution_id' not in columns:
                # Add institution_id column with default value of 1 for existing records
                op.add_column(table, sa.Column('institution_id', sa.Integer(), nullable=False, server_default='1'))
                
                # Create index on institution_id for better query performance
                op.create_index(f'ix_{table}_institution_id', table, ['institution_id'])
                
                # Remove server default after setting values
                op.alter_column(table, 'institution_id', server_default=None)
                
                print(f"Added institution_id to {table}")
            else:
                print(f"institution_id already exists in {table}, skipping...")
        except Exception as e:
            print(f"Error adding institution_id to {table}: {e}")
            # Continue with other tables even if one fails
            continue


def downgrade() -> None:
    """Remove institution_id column from all tables."""
    tables = [
        'students',
        'teachers',
        'courses',
        'schedules',
        'student_records',
        'complaints',
        'assignments',
        'assignment_submissions',
        'enrollments',
        'departments',
        'classes',
        'academic_years',
        'guardians'
    ]
    
    for table in tables:
        try:
            # Check if column exists before dropping
            connection = op.get_bind()
            inspector = sa.inspect(connection)
            columns = [col['name'] for col in inspector.get_columns(table)]
            
            if 'institution_id' in columns:
                # Drop index first
                try:
                    op.drop_index(f'ix_{table}_institution_id', table_name=table)
                except Exception:
                    pass  # Index might not exist
                
                # Drop column
                op.drop_column(table, 'institution_id')
                
                print(f"Removed institution_id from {table}")
            else:
                print(f"institution_id does not exist in {table}, skipping...")
        except Exception as e:
            print(f"Error removing institution_id from {table}: {e}")
            # Continue with other tables even if one fails
            continue
