from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.helpers.analytics_context import (
    format_error_message,
    map_login_failure_reason,
    tenant_id_and_name,
)
from app.services.analytics_service import record_login_event
from app.schemas.login import (
    LoginRequest,
    LoginResponse,
    LoginOtpRequest,
    LoginOtpVerifyRequest,
    LoginOtpRequestResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from app.apis.login import new_login, verify_token, refresh_access_token
from app.services.login_otp_service import request_login_otp, verify_login_otp
from app.dependencies.tenantDependency import get_db, get_tenant

login = APIRouter()

def _client_meta(request: Request) -> tuple:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@login.post("/login", response_model=LoginResponse)
async def login_user(
    login_request: LoginRequest,
    request: Request,
    tenant_name: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """User login (requires X-Tenant-Name header)"""
    ip_address, user_agent = _client_meta(request)
    identifier = login_request.username
    tid, tname = tenant_id_and_name(tenant_name=tenant_name)
    try:
        result = await new_login(loginRequest=login_request, db=db, tenant_name=tenant_name)
        u = result.user
        record_login_event(
            method="password",
            outcome="success",
            tenant_id=u.institution_id if u else tid,
            tenant_name=result.tenantName or tname,
            user_id=u.id if u else None,
            identifier=identifier,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return result
    except HTTPException as exc:
        from app.models.user import User
        from sqlalchemy import or_

        detail_text = format_error_message(exc.detail)
        failure_reason = map_login_failure_reason(exc.detail)

        user_for_audit = (
            db.query(User)
            .filter(
                or_(User.username == identifier, User.email == identifier),
                User.deleted_at.is_(None),
            )
            .first()
        )
        if user_for_audit and user_for_audit.institution_id:
            tid, tname = tenant_id_and_name(tenant_name=tenant_name, user=user_for_audit)

        record_login_event(
            method="password",
            outcome="failure",
            failure_reason=failure_reason,
            failure_detail=detail_text,
            tenant_id=tid,
            tenant_name=tname,
            user_id=user_for_audit.id if user_for_audit else None,
            identifier=identifier,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        request.state.error_recorded = True
        raise
    

@login.post("/verify_token")
async def validate_token(request: Request):
    """Verify JWT token validity"""
    tokenData = await request.json()
    token: str = tokenData.get('access_token')
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="access_token is required"
        )
    return await verify_token(token)

@login.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token_endpoint(refresh_request: RefreshTokenRequest):
    """Refresh access token using refresh token (no tenant header required)"""
    return await refresh_access_token(refresh_request.refresh_token)


@login.post("/login/otp/request", response_model=LoginOtpRequestResponse)
async def login_otp_request(
    body: LoginOtpRequest,
    request: Request,
    tenant_name: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """Send a one-time sign-in code to the user's registered email."""
    ip_address, user_agent = _client_meta(request)
    return await request_login_otp(
        db=db,
        email=body.email,
        tenant_name=tenant_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@login.post("/login/otp/verify", response_model=LoginResponse)
async def login_otp_verify(
    body: LoginOtpVerifyRequest,
    request: Request,
    tenant_name: str = Depends(get_tenant),
    db: Session = Depends(get_db),
):
    """Verify email OTP and return the same tokens as password login."""
    ip_address, user_agent = _client_meta(request)
    try:
        result = await verify_login_otp(
            db=db, email=body.email, otp=body.otp, tenant_name=tenant_name
        )
    except HTTPException:
        request.state.error_recorded = True
        raise
    u = result.user
    record_login_event(
        method="otp_verify",
        outcome="success",
        tenant_id=u.institution_id if u else None,
        tenant_name=result.tenantName or tenant_name,
        user_id=u.id if u else None,
        identifier=body.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result