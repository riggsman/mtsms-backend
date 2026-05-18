"""Resolve tenant context for analytics events."""

from __future__ import annotations

import json
from typing import Any, Optional, Tuple

from starlette.requests import Request

from app.conf.config import settings
from app.database.base import DefaultSessionLocal
from app.models.tenant import Tenant
from app.models.user import User


def tenant_id_and_name(
    tenant_name: Optional[str] = None,
    user: Optional[User] = None,
) -> Tuple[Optional[int], Optional[str]]:
    if user is not None and user.institution_id:
        tid = int(user.institution_id)
        name = tenant_name
        if not name:
            db = DefaultSessionLocal()
            try:
                tenant = db.query(Tenant).filter(Tenant.id == tid).first()
                name = tenant.name if tenant else None
            finally:
                db.close()
        return tid, name

    if not tenant_name:
        return None, None

    db = DefaultSessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
        if tenant:
            return tenant.id, tenant.name
        return None, tenant_name
    finally:
        db.close()


def map_login_failure_reason(detail: Any) -> str:
    d = format_error_message(detail).lower()
    if "username" in d or "user not found" in d:
        return "invalid_username"
    if "password" in d:
        return "invalid_password"
    if "inactive" in d or "not active" in d:
        return "inactive_account"
    if "missing" in d:
        return "missing_credentials"
    if "expired" in d:
        return "token_expired"
    if "otp" in d or "sign-in code" in d:
        return "invalid_otp"
    return "unknown"


def format_error_message(detail: Any) -> str:
    if detail is None:
        return "Unknown error"
    if isinstance(detail, str):
        return detail[:2000]
    try:
        return json.dumps(detail, default=str)[:2000]
    except Exception:
        return str(detail)[:2000]


def error_type_from_status(status_code: int) -> str:
    if status_code >= 500:
        return "server_error"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code == 422:
        return "validation_error"
    if status_code >= 400:
        return "client_error"
    return "unknown"


def resolve_request_context(request: Request) -> Tuple[Optional[int], Optional[str], Optional[int]]:
    tenant_id: Optional[int] = None
    tenant_name = request.headers.get("X-Tenant-Name")
    user_id: Optional[int] = None

    inst_header = request.headers.get("X-Institution-Id")
    if inst_header:
        try:
            tenant_id = int(inst_header)
        except ValueError:
            pass

    auth = request.headers.get("Authorization")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            try:
                from jose import jwt

                payload = jwt.decode(
                    parts[1],
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                )
                user_id_raw = payload.get("sub")
                if user_id_raw is not None:
                    user_id = int(user_id_raw)
                if tenant_id is None and payload.get("institution_id") is not None:
                    tenant_id = int(payload["institution_id"])
            except Exception:
                pass

    return tenant_id, tenant_name, user_id


def classify_email_failure(failure_reason: Optional[str]) -> tuple[str, str]:
    """Return (error_type, message) for platform analytics."""
    message = (failure_reason or "Email delivery failed").strip()
    lower = message.lower()
    if (
        "invalid credentials" in lower
        or "authentication failed" in lower
        or "smtpauthenticationerror" in lower
        or "535" in lower
        or "username and password" in lower
        or ("auth" in lower and "fail" in lower)
    ):
        return "smtp_invalid_credentials", message
    if "smtp credentials not configured" in lower or "not configured" in lower:
        return "smtp_not_configured", message
    if "disabled" in lower and "email" in lower:
        return "email_disabled", message
    return "email_delivery_failed", message


def route_template_from_request(request: Request) -> Optional[str]:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path
