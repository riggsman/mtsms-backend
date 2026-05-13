"""add firebase storage_bucket and measurement_id columns

Revision ID: add_firebase_storage_meas
Revises: 20260221_fcm_tokens
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_firebase_storage_meas"
down_revision: Union[str, Sequence[str], None] = "20260221_fcm_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column("firebase_storage_bucket", sa.String(255), nullable=True),
    )
    op.add_column(
        "system_settings",
        sa.Column("firebase_measurement_id", sa.String(255), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE system_settings SET "
            "firebase_api_key = 'AIzaSyC5ju7WE_Uc5KXM0wqMUtwmfhHIo4ZPPyA', "
            "firebase_auth_domain = 'wireit-91b12.firebaseapp.com', "
            "firebase_project_id = 'wireit-91b12', "
            "firebase_storage_bucket = 'wireit-91b12.appspot.com', "
            "firebase_messaging_sender_id = '204834509466', "
            "firebase_app_id = '1:204834509466:web:722803d25b5a21f8ff4523', "
            "firebase_measurement_id = 'G-HK25N9X6SG', "
            "firebase_messaging_enabled = 1 "
            "WHERE id = 1"
        )
    )


def downgrade() -> None:
    op.drop_column("system_settings", "firebase_measurement_id")
    op.drop_column("system_settings", "firebase_storage_bucket")