"""Record API and unhandled errors for platform analytics."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.helpers.analytics_context import (
    error_type_from_status,
    format_error_message,
    map_login_failure_reason,
    resolve_request_context,
    route_template_from_request,
)
from app.services.analytics_service import record_platform_error

logger = logging.getLogger(__name__)


def _mark_recorded(request: Request) -> None:
    request.state.error_recorded = True


def _is_recorded(request: Request) -> bool:
    return bool(getattr(request.state, "error_recorded", False))


def _record_api_error(
    request: Request,
    *,
    message: str,
    status_code: int,
    error_type: str,
) -> None:
    if _is_recorded(request):
        return
    tenant_id, tenant_name, user_id = resolve_request_context(request)
    path = request.url.path
    source = "login" if "/login" in path or path.startswith("/auth/") else "api"
    resolved_type = error_type
    if source == "login":
        mapped = map_login_failure_reason(message)
        if mapped != "unknown":
            resolved_type = mapped
    record_platform_error(
        source=source,
        error_type=resolved_type,
        message=message,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        user_id=user_id,
        status_code=status_code,
        method=request.method,
        path=path,
        route_template=route_template_from_request(request),
    )
    _mark_recorded(request)


def register_platform_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code >= 400:
            _record_api_error(
                request,
                message=format_error_message(exc.detail),
                status_code=exc.status_code,
                error_type=error_type_from_status(exc.status_code),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 400:
            _record_api_error(
                request,
                message=format_error_message(exc.detail),
                status_code=exc.status_code,
                error_type=error_type_from_status(exc.status_code),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        _record_api_error(
            request,
            message=format_error_message(exc.errors()),
            status_code=422,
            error_type="validation_error",
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        _record_api_error(
            request,
            message=str(exc)[:2000],
            status_code=500,
            error_type="unhandled",
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
