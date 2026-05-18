"""Log tenant-scoped API requests to platform analytics store."""

from __future__ import annotations

import logging
import time
from starlette.requests import Request

from app.helpers.analytics_context import (
    error_type_from_status,
    resolve_request_context,
    route_template_from_request,
)
from app.services.analytics_service import record_api_request, record_platform_error

logger = logging.getLogger(__name__)

_SKIP_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
)


def _should_log(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return False
    if any(path.startswith(p) for p in _SKIP_PREFIXES):
        return False
    return path.startswith("/api/") or path.startswith("/auth/")


async def analytics_middleware(request: Request, call_next):
    if not _should_log(request.url.path, request.method):
        return await call_next(request)

    tenant_id, tenant_name, user_id = resolve_request_context(request)
    route_tpl = route_template_from_request(request)
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        if not getattr(request.state, "error_recorded", False):
            record_platform_error(
                source="api",
                error_type="unhandled",
                message=str(exc)[:2000],
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                user_id=user_id,
                status_code=500,
                method=request.method,
                path=request.url.path,
                route_template=route_tpl,
            )
            request.state.error_recorded = True
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)

    try:
        record_api_request(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            user_id=user_id,
            method=request.method,
            path=request.url.path,
            route_template=route_tpl,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        if (
            response.status_code >= 400
            and not getattr(request.state, "error_recorded", False)
        ):
            record_platform_error(
                source="api",
                error_type=error_type_from_status(response.status_code),
                message=f"HTTP {response.status_code} on {request.method} {route_tpl or request.url.path}",
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                user_id=user_id,
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
                route_template=route_tpl,
            )
    except Exception as exc:
        logger.debug("API analytics record skipped: %s", exc)

    return response
