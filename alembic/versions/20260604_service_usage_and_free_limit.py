"""Add service usage tracker and free-download limit column.

Revision ID: 20260604_service_usage_and_free_limit
Revises: 20260604_tenant_current_semester
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_service_usage_and_free_limit"
down_revision = "20260604_tenant_current_semester"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "subscription_services" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("subscription_services")}
        if "max_free_download" not in columns:
            op.add_column("subscription_services", sa.Column("max_free_download", sa.Integer(), nullable=True))

    if "student_service_usage" not in inspector.get_table_names():
        op.create_table(
            "student_service_usage",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("service_key", sa.String(length=120), nullable=False),
            sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "institution_id", "student_id", "service_key", name="uq_student_service_usage"
            ),
        )
        op.create_index(
            "ix_student_service_usage_institution_id", "student_service_usage", ["institution_id"]
        )
        op.create_index("ix_student_service_usage_student_id", "student_service_usage", ["student_id"])
        op.create_index("ix_student_service_usage_service_key", "student_service_usage", ["service_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "student_service_usage" in inspector.get_table_names():
        op.drop_index("ix_student_service_usage_service_key", table_name="student_service_usage")
        op.drop_index("ix_student_service_usage_student_id", table_name="student_service_usage")
        op.drop_index("ix_student_service_usage_institution_id", table_name="student_service_usage")
        op.drop_table("student_service_usage")

    if "subscription_services" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("subscription_services")}
        if "max_free_download" in columns:
            op.drop_column("subscription_services", "max_free_download")

"""Add service usage tracker and free-download limit column.

Revision ID: 20260604_service_usage_and_free_limit
Revises: 20260604_tenant_current_semester
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_service_usage_and_free_limit"
down_revision = "20260604_tenant_current_semester"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "subscription_services" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("subscription_services")}
        if "max_free_download" not in columns:
            op.add_column("subscription_services", sa.Column("max_free_download", sa.Integer(), nullable=True))

    if "student_service_usage" not in inspector.get_table_names():
        op.create_table(
            "student_service_usage",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("service_key", sa.String(length=120), nullable=False),
            sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "institution_id", "student_id", "service_key", name="uq_student_service_usage"
            ),
        )
        op.create_index(
            "ix_student_service_usage_institution_id", "student_service_usage", ["institution_id"]
        )
        op.create_index("ix_student_service_usage_student_id", "student_service_usage", ["student_id"])
        op.create_index("ix_student_service_usage_service_key", "student_service_usage", ["service_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "student_service_usage" in inspector.get_table_names():
        op.drop_index("ix_student_service_usage_service_key", table_name="student_service_usage")
        op.drop_index("ix_student_service_usage_student_id", table_name="student_service_usage")
        op.drop_index("ix_student_service_usage_institution_id", table_name="student_service_usage")
        op.drop_table("student_service_usage")

    if "subscription_services" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("subscription_services")}
        if "max_free_download" in columns:
            op.drop_column("subscription_services", "max_free_download")

