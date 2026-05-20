"""Tenant services activation guard for tenant-scoped API routes."""

from __future__ import annotations

import datetime
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
from app.helpers.user_roles import user_is_system_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.services import feature_access_service as fas


def get_platform_support_settings(db: Session) -> dict:
    from app.models.system_settings import SystemSettings

    settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    if not settings:
        return {
            "platform_support_email": None,
            "platform_support_phone": None,
            "platform_support_hours": None,
        }
    return {
        "platform_support_email": settings.platform_support_email,
        "platform_support_phone": settings.platform_support_phone,
        "platform_support_hours": settings.platform_support_hours,
    }


def _coerce_db_bool(val) -> bool:
    if val is True or val == 1:
        return True
    if isinstance(val, bytes):
        return val in (b"\x01", b"1")
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "t")
    return False


def read_services_activated_from_db(db: Session, tenant_id: int) -> Optional[bool]:
    """Read services_activated directly from MySQL (avoids ORM/type coercion issues)."""
    try:
        row = db.execute(
            text("SELECT services_activated FROM tenants WHERE id = :tid LIMIT 1"),
            {"tid": tenant_id},
        ).first()
    except Exception:
        return None
    if row is None:
        return None
    return _coerce_db_bool(row[0])


def count_enabled_entitlements(db: Session, tenant: Optional[Tenant]) -> int:
    """Count feature rows explicitly enabled for this tenant in tenant_feature_entitlements."""
    if not tenant:
        return 0
    from app.models.tenant_feature_entitlement import TenantFeatureEntitlement

    return (
        db.query(TenantFeatureEntitlement)
        .filter(
            TenantFeatureEntitlement.tenant_id == tenant.id,
            TenantFeatureEntitlement.is_enabled.is_(True),
        )
        .count()
    )


def count_effective_features(db: Session, tenant: Optional[Tenant]) -> int:
    """Features effectively available to the tenant (plan + entitlements)."""
    if not tenant:
        return 0
    from app.services import feature_access_service as fas

    data = fas.get_tenant_feature_matrix(db, tenant)
    return sum(1 for item in data.get("items", []) if item.get("effective"))


def count_activated_features(db: Session, tenant: Optional[Tenant]) -> int:
    """Enabled services for activation checks (explicit entitlements, else effective)."""
    explicit = count_enabled_entitlements(db, tenant)
    if explicit > 0:
        return explicit
    return count_effective_features(db, tenant)


def set_tenant_services_activated(
    db: Session,
    tenant: Tenant,
    *,
    activated: bool,
    activated_by_user_id: Optional[int] = None,
    require_features_when_activating: bool = True,
) -> Tenant:
    if activated and require_features_when_activating:
        if count_activated_features(db, tenant) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enable at least one service for this tenant before activation.",
            )
    tenant.services_activated = bool(activated)
    if activated:
        tenant.services_activated_at = datetime.datetime.utcnow()
        tenant.services_activated_by = activated_by_user_id
    else:
        tenant.services_activated_at = None
        tenant.services_activated_by = None
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def raise_if_tenant_suspended_for_login(db: Session, user: User) -> None:
    """Block password/OTP login and token refresh for users of a suspended tenant."""
    if user_is_system_admin(user):
        return
    institution_id = getattr(user, "institution_id", None)
    if not institution_id:
        return
    tenant = db.query(Tenant).filter(Tenant.id == institution_id).first()
    if tenant is None:
        return
    if not is_tenant_suspended(tenant, db):
        return
    reason = getattr(tenant, "suspension_reason", None) or ""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "TENANT_SUSPENDED",
            "message": "This institution has been suspended. Contact platform support.",
            "reason": reason[:500] if reason else None,
        },
    )


def is_tenant_suspended(
    tenant: Optional[Tenant],
    db: Optional[Session] = None,
) -> bool:
    """Suspended = inactive with explicit suspension metadata from system admin."""
    if tenant is None:
        return False

    is_active = True
    reason = getattr(tenant, "suspension_reason", None)
    suspended_at = getattr(tenant, "suspended_at", None)

    if db is not None:
        try:
            row = db.execute(
                text(
                    "SELECT is_active, suspension_reason, suspended_at "
                    "FROM tenants WHERE id = :tid LIMIT 1"
                ),
                {"tid": tenant.id},
            ).first()
            if row is not None:
                is_active = _coerce_db_bool(row[0])
                reason = row[1]
                suspended_at = row[2]
        except Exception:
            pass

    if _coerce_db_bool(is_active):
        return False
    return bool(reason) or suspended_at is not None


def is_tenant_services_activated(
    tenant: Optional[Tenant],
    db: Optional[Session] = None,
) -> bool:
    """Read activation flag from DB row (source of truth), with ORM fallback."""
    if tenant is None:
        return False
    if db is not None:
        raw = read_services_activated_from_db(db, tenant.id)
        if raw is not None:
            return raw
    return _coerce_db_bool(getattr(tenant, "services_activated", False))


def resolve_tenant_for_user(
    db: Session,
    user: User,
    x_tenant_domain: Optional[str] = None,
    x_tenant_name: Optional[str] = None,
) -> Optional[Tenant]:
    from app.apis.tenant import get_tenant_by_id, get_tenant_by_name

    tenant: Optional[Tenant] = None
    institution_id = getattr(user, "institution_id", None)

    if institution_id:
        try:
            tenant = get_tenant_by_id(db, institution_id)
        except Exception:
            tenant = db.query(Tenant).filter(Tenant.id == institution_id).first()

    domain_hint = (x_tenant_domain or x_tenant_name or "").strip() or None
    if tenant is None and domain_hint:
        try:
            tenant = get_tenant_by_name(db, domain_hint)
        except Exception:
            tenant = fas.resolve_tenant(db, institution_id=None, domain=domain_hint)

    if tenant is None and domain_hint is None:
        tenant = fas.resolve_tenant(db, institution_id=institution_id, domain=None)

    if tenant is not None:
        tenant = db.query(Tenant).filter(Tenant.id == tenant.id).first()
    return tenant


def require_tenant_services_activated(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    x_tenant_domain: Optional[str] = Header(None, alias="X-Tenant-Domain"),
    x_tenant_name: Optional[str] = Header(None, alias="X-Tenant-Name"),
) -> User:
    if user_is_system_admin(current_user):
        return current_user

    tenant = resolve_tenant_for_user(db, current_user, x_tenant_domain, x_tenant_name)
    if tenant is None:
        return current_user

    if not is_tenant_services_activated(tenant, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TENANT_SERVICES_NOT_ACTIVATED",
                "message": "Tenant services are not activated. Contact platform support.",
            },
        )
    return current_user
