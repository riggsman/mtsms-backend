"""System-admin platform analytics read APIs."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
from app.helpers.user_roles import user_is_tenant_super_admin_or_system
from app.models.user import User
from app.services import platform_analytics_queries as paq


def check_system_admin(current_user: User) -> None:
    if not user_is_tenant_super_admin_or_system(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required system admin role",
        )

router = APIRouter()


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00").split("+")[0])
    except ValueError:
        return None


@router.get("/system/analytics/platform/summary")
async def platform_analytics_summary(
    from_date: Optional[str] = Query(None, alias="from_date"),
    to_date: Optional[str] = Query(None, alias="to_date"),
    tenant_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_summary(db, _parse_date(from_date), _parse_date(to_date), tenant_id)


@router.get("/system/analytics/platform/login-failures")
async def platform_login_failures(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_login_failures(
        db, _parse_date(from_date), _parse_date(to_date), tenant_id, page, page_size
    )


@router.get("/system/analytics/platform/emails")
async def platform_email_analytics(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_email_analytics(
        db, _parse_date(from_date), _parse_date(to_date), tenant_id
    )


@router.get("/system/analytics/platform/otp")
async def platform_otp_analytics(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_otp_analytics(
        db, _parse_date(from_date), _parse_date(to_date), tenant_id
    )


@router.get("/system/analytics/platform/requests")
async def platform_request_analytics(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_request_analytics(
        db, _parse_date(from_date), _parse_date(to_date), tenant_id
    )


@router.get("/system/analytics/platform/errors")
async def platform_errors(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_platform_errors(
        db,
        _parse_date(from_date),
        _parse_date(to_date),
        tenant_id,
        page,
        page_size,
        source,
    )


@router.get("/system/analytics/platform/tenants-matrix")
async def platform_tenants_matrix(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    check_system_admin(current_user)
    return paq.get_tenants_matrix(db, _parse_date(from_date), _parse_date(to_date))
