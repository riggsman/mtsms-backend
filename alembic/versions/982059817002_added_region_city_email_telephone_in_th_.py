"""add tenant location and contact fields

Revision ID: 982059817002
Revises: 20260526_cal_date_range
Create Date: 2026-05-17 21:46:25.174410
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "982059817002"
down_revision: Union[str, Sequence[str], None] = "20260526_cal_date_range"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _table_unique_constraints(table_name: str) -> dict[str, tuple[str, ...]]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return {}
    return {
        constraint["name"]: tuple(constraint.get("column_names") or ())
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _table_unique_indexes(table_name: str) -> dict[str, tuple[str, ...]]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return {}
    return {
        index["name"]: tuple(index.get("column_names") or ())
        for index in inspector.get_indexes(table_name)
        if index.get("unique") and index.get("name")
    }


def _has_unique_on(table_name: str, column_name: str) -> bool:
    expected = (column_name,)
    unique_constraints = _table_unique_constraints(table_name)
    unique_indexes = _table_unique_indexes(table_name)
    return expected in unique_constraints.values() or expected in unique_indexes.values()


def upgrade() -> None:
    """Add tenant location/contact columns without touching unrelated tables."""
    columns = _table_columns("tenants")
    if not columns:
        return

    with op.batch_alter_table("tenants", schema=None) as batch_op:
        if "region" not in columns:
            batch_op.add_column(sa.Column("region", sa.String(length=70), nullable=True))
        if "city" not in columns:
            batch_op.add_column(sa.Column("city", sa.String(length=70), nullable=True))
        if "neighbourhood" not in columns:
            batch_op.add_column(sa.Column("neighbourhood", sa.String(length=70), nullable=True))
        if "email" not in columns:
            batch_op.add_column(sa.Column("email", sa.String(length=70), nullable=True))
        if "telephone" not in columns:
            batch_op.add_column(sa.Column("telephone", sa.String(length=70), nullable=True))

    indexes = _table_indexes("tenants")
    if "ix_tenants_neighbourhood" not in indexes:
        op.create_index(
            "ix_tenants_neighbourhood",
            "tenants",
            ["neighbourhood"],
            unique=False,
        )

    with op.batch_alter_table("tenants", schema=None) as batch_op:
        if not _has_unique_on("tenants", "email"):
            batch_op.create_unique_constraint("uq_tenants_email", ["email"])
        if not _has_unique_on("tenants", "telephone"):
            batch_op.create_unique_constraint("uq_tenants_telephone", ["telephone"])


def downgrade() -> None:
    """Remove only the tenant columns introduced by this revision."""
    columns = _table_columns("tenants")
    if not columns:
        return

    indexes = _table_indexes("tenants")
    unique_constraints = _table_unique_constraints("tenants")
    unique_indexes = _table_unique_indexes("tenants")

    with op.batch_alter_table("tenants", schema=None) as batch_op:
        if "uq_tenants_telephone" in unique_constraints:
            batch_op.drop_constraint("uq_tenants_telephone", type_="unique")
        elif "uq_tenants_telephone" in unique_indexes:
            batch_op.drop_index("uq_tenants_telephone")
        if "uq_tenants_email" in unique_constraints:
            batch_op.drop_constraint("uq_tenants_email", type_="unique")
        elif "uq_tenants_email" in unique_indexes:
            batch_op.drop_index("uq_tenants_email")
        if "ix_tenants_neighbourhood" in indexes:
            batch_op.drop_index("ix_tenants_neighbourhood")
        if "telephone" in columns:
            batch_op.drop_column("telephone")
        if "email" in columns:
            batch_op.drop_column("email")
        if "neighbourhood" in columns:
            batch_op.drop_column("neighbourhood")
        if "city" in columns:
            batch_op.drop_column("city")
        if "region" in columns:
            batch_op.drop_column("region")
