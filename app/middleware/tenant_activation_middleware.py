"""HTTP middleware: block tenant business APIs when services are not activated."""

from __future__ import annotations

import json
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.authentication.authenticator import verify_and_decode_access_token
from app.database.base import DefaultSessionLocal
from app.helpers.user_roles import user_is_system_admin
from app.models.user import User

ACTIVATION_EXEMPT_PREFIXES = (
    "/api/v1/tenant/access-status",
    "/api/v1/tenant/features",
    "/api/v1/tenant/check-service-access",
    "/api/v1/system/maintenance-mode",
    "/api/v1/system/settings/state",
    "/api/v1/system/firebase-web-config",
    "/api/v1/system/cache-version",
    "/api/v1/contact",
    "/api/v1/register",
    "/api/v1/admin/",
    "/api/v1/users/me/",
)

ACTIVATION_EXEMPT_EXACT = (
    "/api/v1/tenants/me",
)


def _path_is_exempt(path: str) -> bool:
    if path in ACTIVATION_EXEMPT_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in ACTIVATION_EXEMPT_PREFIXES)


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
    if not path.startswith("/api/v1"):
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

        if is_tenant_suspended(tenant, db):
            reason = getattr(tenant, "suspension_reason", None) or ""
            body = {
                "detail": {
                    "code": "TENANT_SUSPENDED",
                    "message": "This institution has been suspended. Contact platform support.",
                    "reason": reason[:500] if reason else None,
                }
            }
            return JSONResponse(status_code=403, content=body)

        if not is_tenant_services_activated(tenant, db):
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
