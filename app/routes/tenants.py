from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.tenant import TenantRequest, TenantResponse, TenantUpdate
from app.apis.tenant import (
    create_new_tenant, get_tenant_by_name, get_tenant_by_id,
    get_all_tenants, update_tenant, delete_tenant
)
from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
from app.helpers.pagination import PaginatedResponse
from fastapi import HTTPException, status
from app.models.user import User
from app.models.role import UserRole

tenant = APIRouter()

def check_system_admin(current_user: User):
    """Helper to check if user is system admin"""
    if (current_user.role != UserRole.SUPER_ADMIN.value and 
        not (current_user.role and current_user.role.startswith('system_'))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required one of: ['super_admin', 'system_super_admin']"
        )

@tenant.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    tenant_request: TenantRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new tenant (requires SUPER_ADMIN or system_super_admin role)"""
    try:
        check_system_admin(current_user)
        return await create_new_tenant(db=db, tenant=tenant_request)
    except Exception as e:
        from app.helpers.logger import logger
        import traceback
        logger.error(f"Error creating tenant: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tenant: {str(e)}"
        )

@tenant.get("/tenants", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of all tenants with pagination (requires system admin role)"""
    check_system_admin(current_user)
    skip = (page - 1) * page_size
    tenants, total = get_all_tenants(db=db, skip=skip, limit=page_size)
    return PaginatedResponse.create(
        items=tenants,
        total=total,
        page=page,
        page_size=page_size
    )

@tenant.get("/tenants/{identifier}", response_model=TenantResponse)
async def get_tenant_info(
    identifier: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get tenant information by name or ID (requires SUPER_ADMIN or system_super_admin role)"""
    check_system_admin(current_user)
    
    # Try to parse as integer (ID)
    try:
        tenant_id = int(identifier)
        tenant = get_tenant_by_id(db, tenant_id)
        return tenant
    except ValueError:
        # Not an integer, treat as name
        tenant = get_tenant_by_name(db, identifier)
        if not tenant:
            from app.exceptions import NotFoundError
            raise NotFoundError(f"Tenant '{identifier}' not found")
        return tenant

@tenant.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant_endpoint(
    tenant_id: int,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update a tenant (requires system admin role)"""
    check_system_admin(current_user)
    return update_tenant(db=db, tenant_id=tenant_id, tenant_update=tenant_update)

@tenant.delete("/tenants/{tenant_id}", status_code=204)
async def delete_tenant_endpoint(
    tenant_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a tenant (requires system admin role)"""
    check_system_admin(current_user)
    delete_tenant(db=db, tenant_id=tenant_id)
    return None