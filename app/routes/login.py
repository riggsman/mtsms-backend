from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.login import LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse
from app.apis.login import new_login, verify_token, refresh_access_token
from app.dependencies.tenantDependency import get_db, get_tenant

login = APIRouter()

@login.post("/login", response_model=LoginResponse)
async def login_user(
    login_request: LoginRequest,
    tenant_name: str = Depends(get_tenant),
    db: Session = Depends(get_db)
):
    """User login (requires X-Tenant-Name header)"""
    return await new_login(loginRequest=login_request, db=db, tenant_name=tenant_name)

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