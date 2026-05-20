"""Tenant data isolation helpers (institution_id + domain)."""

from __future__ import annotations

from typing import Any, Optional, Type

from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError, NotFoundError
from app.helpers.user_roles import user_is_system_admin, user_requires_tenant_scope_for_data


def institution_id_for_user(
    user: Any,
    *,
    header_institution_id: Optional[int] = None,
    body_institution_id: Optional[int] = None,
) -> Optional[int]:
    """
    Resolve institution_id for DB queries.
    Tenant users are always limited to user.institution_id.
    System admins may pass an explicit institution (header/body) or None (all).
    """
    if user_is_system_admin(user):
        return header_institution_id if header_institution_id is not None else body_institution_id

    if not getattr(user, "institution_id", None):
        raise ForbiddenError("User must belong to an institution to access tenant data")

    requested = header_institution_id if header_institution_id is not None else body_institution_id
    if requested is not None and requested != user.institution_id:
        raise ForbiddenError(
            f"You can only access data for your institution (ID: {user.institution_id})"
        )
    return user.institution_id


def institution_id_from_user(
    user: Any,
    institution_id: Optional[int] = None,
) -> Optional[int]:
    """API-layer helper: enforce tenant user's institution when current_user is provided."""
    if user is None:
        return institution_id
    if user_is_system_admin(user):
        return institution_id
    if user_requires_tenant_scope_for_data(user):
        if institution_id is not None and institution_id != user.institution_id:
            raise ForbiddenError(
                f"You can only access data for your institution (ID: {user.institution_id})"
            )
        return user.institution_id
    return institution_id


def require_institution_id_for_user(
    user: Any,
    *,
    header_institution_id: Optional[int] = None,
    body_institution_id: Optional[int] = None,
) -> int:
    institution_id = institution_id_for_user(
        user,
        header_institution_id=header_institution_id,
        body_institution_id=body_institution_id,
    )
    if institution_id is None:
        raise ForbiddenError("institution_id is required for this operation")
    return institution_id


def scoped_get_by_id(
    db: Session,
    model: Type,
    record_id: int,
    institution_id: Optional[int] = None,
    *,
    not_found_label: Optional[str] = None,
    soft_delete: bool = True,
):
    """Fetch one row by id; optional institution_id filter (shared DB isolation)."""
    label = not_found_label or getattr(model, "__tablename__", "Record").replace("_", " ").title()
    query = db.query(model).filter(model.id == record_id)
    if soft_delete and hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    if institution_id is not None and hasattr(model, "institution_id"):
        query = query.filter(model.institution_id == institution_id)
    row = query.first()
    if not row:
        raise NotFoundError(f"{label} with ID {record_id} not found")
    return row


def tenant_domain_matches(tenant: Any, tenant_key: str) -> bool:
    """True if tenant_key matches tenant.name or tenant.domain (case-insensitive)."""
    if not tenant_key or not tenant:
        return False
    key = str(tenant_key).strip().lower()
    name = (getattr(tenant, "name", None) or "").strip().lower()
    domain = (getattr(tenant, "domain", None) or "").strip().lower()
    return key in {name, domain} if key else False
