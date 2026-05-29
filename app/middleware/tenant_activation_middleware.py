"""HTTP middleware: block tenant business APIs when services are not activated."""

from __future__ import annotations

import json
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.authentication.authenticator import verify_and_decode_access_token
from app.database.base import DefaultSessionLocal
from app.helpers.user_roles import user_is_system_admin
from app.helpers.tenant_activation_cache import (
    get_tenant_access_status,
    set_tenant_access_status,
)
from app.models.user import User

ACTIVATION_EXEMPT_PREFIXES = (
    "/tenant/access-status",
    "/tenant/features",
    "/tenant/check-service-access",
    "/certificates/",
    "/transcript",
    "/result-slip",
    "/system/maintenance-mode",
    "/system/settings/state",
    "/system/firebase-web-config",
    "/system/cache-version",
    "/contact",
    "/register",
    "/admin/",
    "/users/me/",
)

ACTIVATION_EXEMPT_EXACT = (
    "/tenants/me",
)

API_V1_PREFIX = "/api/v1"


def _normalize_api_path(path: str) -> str:
    """Strip API prefix so exempt routes match mounted paths like /api/v1/tenant/access-status."""
    normalized = (path or "/").rstrip("/") or "/"
    if normalized.startswith(API_V1_PREFIX):
        normalized = normalized[len(API_V1_PREFIX) :] or "/"
    return normalized


def _path_is_exempt(path: str) -> bool:
    normalized = _normalize_api_path(path)
    if normalized in ACTIVATION_EXEMPT_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in ACTIVATION_EXEMPT_PREFIXES)


def _load_user_from_request(request: Request, db) -> Optional[User]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    result = verify_and_decode_access_token(token)
    if not result.get("success"):
        return None
    payload = result.get("data") or {}
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()


async def tenant_activation_middleware(request: Request, call_next) -> Response:
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path.rstrip("/") or "/"
    if not path.startswith(""):
        return await call_next(request)
    if _path_is_exempt(path):
        return await call_next(request)

    db = DefaultSessionLocal()
    user = None
    try:
        user = _load_user_from_request(request, db)
        if user is None or user_is_system_admin(user):
            return await call_next(request)

        from app.dependencies.tenant_activation import (
            is_tenant_services_activated,
            is_tenant_suspended,
            resolve_tenant_for_user,
        )

        x_tenant_domain = request.headers.get("x-tenant-domain")
        x_tenant_name = request.headers.get("x-tenant-name")
        tenant = resolve_tenant_for_user(db, user, x_tenant_domain, x_tenant_name)
        if tenant is None:
            return await call_next(request)

        cached_status = get_tenant_access_status(tenant.id)
        if cached_status is not None:
            suspended, activated = cached_status
        else:
            suspended = is_tenant_suspended(tenant, db)
            activated = is_tenant_services_activated(tenant, db)
            set_tenant_access_status(
                tenant.id,
                is_suspended=suspended,
                is_activated=activated,
            )

        if suspended:
            reason = getattr(tenant, "suspension_reason", None) or ""
            body = {
                "detail": {
                    "code": "TENANT_SUSPENDED",
                    "message": "This institution has been suspended. Contact platform support.",
                    "reason": reason[:500] if reason else None,
                }
            }
            return JSONResponse(status_code=403, content=body)

        if not activated:
            body = {
                "detail": {
                    "code": "TENANT_SERVICES_NOT_ACTIVATED",
                    "message": "Tenant services are not activated. Contact platform support.",
                }
            }
            return JSONResponse(status_code=403, content=body)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("tenant_activation_middleware failed")
        if user is not None and not user_is_system_admin(user) and getattr(user, "institution_id", None):
            body = {
                "detail": {
                    "code": "TENANT_ACTIVATION_CHECK_FAILED",
                    "message": "Could not verify tenant activation status. Please try again.",
                }
            }
            return JSONResponse(status_code=503, content=body)
    finally:
        db.close()

    return await call_next(request)
