import argon2
from sqlalchemy import or_
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.authentication.authenticator import create_access_token, create_refresh_token, verify_and_decode_access_token, verify_password
from app.models.user import User
from app.schemas.login import LoginRequest, LoginResponse
from app.database.base import get_db_session
from app.helpers.user_roles import (
    role_string_for_legacy,
    user_is_system_admin,
    user_roles_list,
    user_system_permissions_list,
)


async def new_login(loginRequest: LoginRequest, db: Session, tenant_name: str = None):
    if not loginRequest.username or not loginRequest.password:
        raise HTTPException(status_code=400, detail="Missing username or password")
    else:
        print("USER DATA BEFORE PROCESSING LOGIN REQUEST ", loginRequest.username)
        # Try to find user by username first, then by email
        user = db.query(User).filter(or_(User.username == loginRequest.username, User.email == loginRequest.username)).first()
        print("USER DATA DURING LOGIN REQUEST ", user.username if user else "User not found")
        if not user:
            # If not found by username, try email
            user = db.query(User).filter(User.email == loginRequest.username).first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid username")
        
        if not verify_password(loginRequest.password, user.password):
            raise HTTPException(status_code=400, detail="Invalid password")
        
        # Get tenant name and domain from institution_id if available
        # System admins (roles starting with 'system_') don't need tenant
        tenant_name_from_user = None
        tenant_domain_from_user = None
        is_system_admin = user_is_system_admin(user)
        
        # Always fetch tenant information from database using institution_id
        if not is_system_admin and user.institution_id:
            from app.models.tenant import Tenant
            global_db = next(get_db_session())
            try:
                tenant = global_db.query(Tenant).filter(Tenant.id == user.institution_id).first()
                if tenant:
                    # Always use database values for tenant name and domain
                    tenant_name_from_user = tenant.name
                    tenant_domain_from_user = tenant.domain
                    # Log for debugging
                    print(f"Fetched tenant from database - Name: {tenant_name_from_user}, Domain: {tenant_domain_from_user}")
            except Exception as e:
                print(f"Error fetching tenant from database: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error fetching tenant from database"
                )
            finally:
                global_db.close()
        
        # Prioritize database values over request parameter
        # System admins don't require tenant name
        final_tenant_name = tenant_name_from_user if tenant_name_from_user else (tenant_name if not is_system_admin else None)
        final_domain = tenant_domain_from_user  # Always use domain from database if available
        
        role_for_token = user_roles_list(user)
        data = {
            "sub": user.id.__str__(),
            "username": user.firstname + " " + user.lastname,
            "roles": role_for_token,
            "institution_id": user.institution_id
        }
        
        # Prepare user info for response
        from app.schemas.login import UserInfo
        perm_list = user_system_permissions_list(user) if is_system_admin else []
        user_info = UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            roles=role_for_token,
            role=role_string_for_legacy(user),
            firstname=user.firstname,
            lastname=user.lastname,
            tenantName=final_tenant_name,
            domain=final_domain,
            institution_id=user.institution_id,
            mustChangePassword=getattr(user, 'must_change_password', 'false') == "true",
            language=getattr(user, 'language', 'en') or 'en',
            system_permissions=perm_list if is_system_admin else None,
        )
        
        return LoginResponse(
            access_token=create_access_token(data), 
            refresh_token=create_refresh_token(data),
            token_type="bearer",
            user=user_info,
            tenantName=final_tenant_name,
            domain=final_domain
        )
    

async def verify_token(token: str):
    return verify_and_decode_access_token(token)

async def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token"""
    from app.authentication.authenticator import verify_and_decode_access_token, create_access_token, create_refresh_token
    
    # Verify the refresh token
    token_result = verify_and_decode_access_token(refresh_token)
    
    if not token_result.get("success"):
        error_msg = token_result.get("error", "Invalid refresh token")
        # Ensure we return "Token has expired" if that's the error
        if "expired" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Token has expired")
        raise HTTPException(status_code=401, detail=error_msg)
    
    # Extract user data from refresh token
    payload = token_result.get("data")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")
    
    # Get user from database to ensure user still exists
    # Use global database session
    db = next(get_db_session())
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if user is active
        if user.is_active != "active":
            raise HTTPException(status_code=401, detail="User account is not active")
        
        # Create new tokens with same user data
        role_for_token = user_roles_list(user)
        data = {
            "sub": str(user.id),
            "username": user.firstname + " " + user.lastname,
            "roles": role_for_token,
            "institution_id": user.institution_id
        }
        
        from app.schemas.login import RefreshTokenResponse
        return RefreshTokenResponse(
            access_token=create_access_token(data),
            refresh_token=create_refresh_token(data),
            token_type="bearer"
        )
    finally:
        db.close()
    
