"""merge_heads_20260412

Revision ID: f17c805f87b4
Revises: add_is_due_is_overdue_columns, 20260412_01_add_student_birthplace_degree, add_school_id_to_students
Create Date: 2026-04-12 16:09:48.225080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f17c805f87b4'
down_revision: Union[str, Sequence[str], None] = ('add_is_due_is_overdue_columns', '20260412_01_add_student_birthplace_degree', 'add_school_id_to_students')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
