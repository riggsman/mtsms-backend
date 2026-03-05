"""
Dependency to extract and validate institution_id from request headers.
Ensures tenant isolation by validating institution_id matches the authenticated user's institution.
"""
from fastapi import HTTPException, Header, Depends, status
from typing import Optional
from app.dependencies.auth import get_current_user_tenant
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


def get_institution_id_from_header(
    x_institution_id: Optional[str] = Header(default=None, alias="X-Institution-Id"),
    current_user: User = Depends(get_current_user_tenant)
) -> Optional[int]:
    """
    Extracts and validates institution_id from the X-Institution-Id header.
    
    Rules:
    1. If header is provided, it must match the current user's institution_id (unless user is system admin)
    2. If header is not provided, use the current user's institution_id
    3. System admins (roles starting with 'system_') can access any institution
    4. Non-system users must belong to an institution
    
    Returns:
        int: The validated institution_id
        None: If user is system admin and no institution_id is provided
    
    Raises:
        HTTPException: If institution_id validation fails
    """
    is_system_admin = current_user.role and current_user.role.startswith('system_')
    
    # System admins can access any institution or no institution
    if is_system_admin:
        if x_institution_id:
            try:
                institution_id = int(x_institution_id)
                logger.debug(f"[get_institution_id] System admin accessing institution_id: {institution_id}")
                return institution_id
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid institution_id format: {x_institution_id}"
                )
        # System admin without header - return None (can access all institutions)
        logger.debug("[get_institution_id] System admin - no institution_id header, returning None")
        return None
    
    # Non-system users must belong to an institution
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to perform this operation"
        )
    
    # If header is provided, validate it matches user's institution
    if x_institution_id:
        try:
            header_institution_id = int(x_institution_id)
            if header_institution_id != current_user.institution_id:
                logger.warning(
                    f"[get_institution_id] Institution ID mismatch: "
                    f"header={header_institution_id}, user={current_user.institution_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Institution ID mismatch. You can only access data for your institution (ID: {current_user.institution_id})"
                )
            logger.debug(f"[get_institution_id] Validated institution_id: {header_institution_id}")
            return header_institution_id
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid institution_id format: {x_institution_id}"
            )
    
    # No header provided - use user's institution_id
    logger.debug(f"[get_institution_id] Using user's institution_id: {current_user.institution_id}")
    return current_user.institution_id


def require_institution_id(
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
) -> int:
    """
    Dependency that requires an institution_id to be present.
    Used for endpoints that must operate within a specific institution context.
    
    Raises:
        HTTPException: If institution_id is None
    """
    if institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="institution_id is required for this operation"
        )
    return institution_id
