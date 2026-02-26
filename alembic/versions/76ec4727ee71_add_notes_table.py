"""add_notes_table

Revision ID: 76ec4727ee71
Revises: 9e98d00865bb
Create Date: 2026-02-25 14:31:33.890207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '76ec4727ee71'
down_revision: Union[str, Sequence[str], None] = '9e98d00865bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create notes table."""
    op.create_table('notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('institution_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('course_code', sa.String(length=50), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('lecturer_id', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('pdf_file_path', sa.String(length=500), nullable=True),
    sa.Column('word_file_path', sa.String(length=500), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['lecturer_id'], ['teachers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_id'), 'notes', ['id'], unique=False)
    op.create_index(op.f('ix_notes_institution_id'), 'notes', ['institution_id'], unique=False)
    op.create_index(op.f('ix_notes_course_id'), 'notes', ['course_id'], unique=False)
    op.create_index(op.f('ix_notes_department_id'), 'notes', ['department_id'], unique=False)
    op.create_index(op.f('ix_notes_lecturer_id'), 'notes', ['lecturer_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Drop notes table."""
    op.drop_index(op.f('ix_notes_lecturer_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_department_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_course_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_institution_id'), table_name='notes')
    op.drop_index(op.f('ix_notes_id'), table_name='notes')
    op.drop_table('notes')
