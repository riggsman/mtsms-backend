"""add firebase_service_account_uploaded column

Revision ID: add_firebase_service_uploaded
Revises: add_firebase_storage_meas
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "add_firebase_service_uploaded"
down_revision: Union[str, Sequence[str], None] = "add_firebase_storage_meas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "system_settings" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("system_settings")}
    if "firebase_service_account_uploaded" not in columns:
        op.add_column(
            "system_settings",
            sa.Column(
                "firebase_service_account_uploaded",
                sa.Boolean(),
                default=False,
                nullable=False,
            ),
        )

    from pathlib import Path

    service_account_path = Path("app/firebase/serviceAccount.json")
    if service_account_path.exists():
        op.execute(
            sa.text(
                "UPDATE system_settings SET firebase_service_account_uploaded = 1 WHERE id = 1"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "system_settings" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("system_settings")}
    if "firebase_service_account_uploaded" in columns:
        op.drop_column("system_settings", "firebase_service_account_uploaded")
