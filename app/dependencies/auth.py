from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from app.authentication.authenticator import verify_and_decode_access_token
from app.models.user import User
from app.models.role import UserRole
from app.dependencies.tenantDependency import get_db
from app.database.base import get_db_session

def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    Expects: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    # Verify token
    result = verify_and_decode_access_token(token)
    if not result.get("success"):
        error_msg = result.get("error", "Invalid token")
        # If token expired, check user status before raising error
        if "expired" in error_msg.lower():
            try:
                # Try to decode token without verification to get user_id
                from jose import jwt
                from app.conf.config import settings
                payload_unverified = jwt.decode(token, options={"verify_signature": False})
                user_id = int(payload_unverified.get("sub"))
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active != "active":
                    # User is not active, don't allow refresh
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expired and user is not active"
                    )
            except Exception:
                pass  # If we can't decode, just raise the original error
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg
        )
    
    payload = result["data"]
    user_id = int(payload.get("sub"))
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if user is active
    if user.is_active != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active"
        )
    
    return user


def get_current_user_tenant(
    authorization: str = Header(..., alias="Authorization"),
    x_tenant_name: str = Header(..., alias="X-Tenant-Name"),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from tenant-specific database
    Expects: Authorization: Bearer <token> and X-Tenant-Name header
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    # Verify token
    result = verify_and_decode_access_token(token)
    if not result.get("success"):
        error_msg = result.get("error", "Invalid token")
        # If token expired, check user status before raising error
        if "expired" in error_msg.lower():
            try:
                # Try to decode token without verification to get user_id
                from jose import jwt
                from app.conf.config import settings
                payload_unverified = jwt.decode(token, options={"verify_signature": False})
                user_id = int(payload_unverified.get("sub"))
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active != "active":
                    # User is not active, don't allow refresh
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expired and user is not active"
                    )
            except Exception:
                pass  # If we can't decode, just raise the original error
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg
        )
    
    payload = result["data"]
    user_id = int(payload.get("sub"))
    
    # Get user from tenant database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if user is active
    if user.is_active != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active"
        )
    
    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory to require specific role(s)
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.STAFF))
    Allows system_ prefixed roles (e.g., system_admin, system_super_admin) when checking for admin/super_admin roles
    Also handles case-insensitive role matching for tenant roles
    """
    def role_checker(current_user: User = Depends(get_current_user_tenant)) -> User:
        user_role = current_user.role
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role not found"
            )
        
        allowed_role_values = [role.value for role in allowed_roles]
        user_role_lower = user_role.lower().strip()
        
        # Direct match (case-insensitive)
        if user_role_lower in [val.lower() for val in allowed_role_values]:
            return current_user
        
        # Check if user has system_ role and any allowed role is admin/super_admin
        if user_role_lower.startswith('system_'):
            # Allow system_ roles if checking for admin or super_admin
            if UserRole.ADMIN in allowed_roles or UserRole.SUPER_ADMIN in allowed_roles:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role(s): {allowed_role_values}. Your role: {user_role}"
        )
    return role_checker


def require_any_role(*allowed_roles: UserRole):
    """
    Dependency factory to require any of the specified roles
    Usage: Depends(require_any_role(UserRole.ADMIN, UserRole.TEACHER))
    Allows system_ prefixed roles (e.g., system_admin, system_super_admin) when checking for admin/secretary/super_admin roles
    Also handles case-insensitive role matching for tenant roles
    """
    def role_checker(current_user: User = Depends(get_current_user_tenant)) -> User:
        user_role = current_user.role
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role not found"
            )
        
        allowed_role_values = [role.value for role in allowed_roles]
        user_role_lower = user_role.lower().strip()
        
        # Direct match (case-insensitive)
        if user_role_lower in [val.lower() for val in allowed_role_values]:
            return current_user
        
        # Check if user has system_ role and any allowed role is admin/secretary/super_admin
        if user_role_lower.startswith('system_'):
            # Allow system_ roles if checking for admin, secretary, or super_admin
            if (UserRole.ADMIN in allowed_roles or 
                UserRole.SECRETARY in allowed_roles or 
                UserRole.SUPER_ADMIN in allowed_roles):
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required one of: {allowed_role_values}. Your role: {user_role}"
        )
    return role_checker


def require_any_role_admin(*allowed_roles: UserRole):
    """
    Dependency factory to require any of the specified roles for admin routes
    Uses get_current_user (global database) instead of get_current_user_tenant
    Usage: Depends(require_any_role_admin(UserRole.ADMIN, UserRole.SECRETARY))
    Allows system_ prefixed roles (e.g., system_admin, system_super_admin) when checking for admin/secretary/super_admin roles
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role
        allowed_role_values = [role.value for role in allowed_roles]
        
        # Direct match
        if user_role in allowed_role_values:
            return current_user
        
        # Check if user has system_ role and any allowed role is admin/secretary/super_admin
        if user_role and user_role.startswith('system_'):
            # Allow system_ roles if checking for admin, secretary, or super_admin
            if (UserRole.ADMIN in allowed_roles or 
                UserRole.SECRETARY in allowed_roles or 
                UserRole.SUPER_ADMIN in allowed_roles):
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required one of: {allowed_role_values}"
        )
    return role_checker


def get_current_user_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db_session)
) -> Optional[User]:
    """
    Optional authentication - returns user if token is valid, None otherwise
    Useful for endpoints that work both authenticated and unauthenticated
    """
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
    except ValueError:
        return None
    
    try:
        result = verify_and_decode_access_token(token)
        if not result.get("success"):
            return None
        
        payload = result["data"]
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except Exception:
        return None
