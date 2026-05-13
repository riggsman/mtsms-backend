"""drop old tables

Revision ID: c123456789ab
Revises: 20260423_add_leave_utility_requests
Create Date: 2026-04-23 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c123456789ab'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET FOREIGN_KEY_CHECKS = 0;")
    tables = ['specializations', 'utility_requests', 'student_payment_installments', 'student_payments', 'leave_requests', 'schools', 'fee_installments', 'payroll_time_entries', 'fee_structures', 'school_fees']
    for table in tables:
        try:
            op.drop_table(table)
        except Exception:
            pass
    op.execute("SET FOREIGN_KEY_CHECKS = 1;")


def downgrade() -> None:
    pass