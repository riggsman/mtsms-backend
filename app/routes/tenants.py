from fastapi import APIRouter, Depends, Query, File, UploadFile, Form, Request
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.dependencies.tenantDependency import get_db
from app.schemas.tenant import TenantRequest, TenantResponse, TenantUpdate
from app.apis.tenant import (
    create_new_tenant, get_tenant_by_name, get_tenant_by_id,
    get_all_tenants, update_tenant, delete_tenant
)
from app.database.base import get_db_session
from app.dependencies.auth import get_current_user, get_current_user_tenant
from app.helpers.pagination import PaginatedResponse
from fastapi import HTTPException, status, Header
from app.models.user import User
from app.models.role import UserRole
from typing import Optional

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
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new tenant (requires SUPER_ADMIN or system_super_admin role)
    
    Accepts both JSON and multipart/form-data:
    
    JSON Request (Content-Type: application/json):
    {
        "name": "string",
        "category": "HI" | "SI",
        "domain": "string",
        "database_name": "string",
        "is_active": true/false,
        "admin_username": "string",
        "admin_password": "string",
        "must_change_password": true/false
    }
    
    FormData Request (Content-Type: multipart/form-data):
    - name: Tenant name (required)
    - category: Tenant category - HI or SI (required)
    - domain: Optional tenant domain
    - database_name: Optional database name
    - is_active: Optional active status (true/false string)
    - admin_username: Optional admin username
    - admin_password: Optional admin password
    - must_change_password: Optional flag (true/false string)
    - logo: Optional logo file upload
    """
    check_system_admin(current_user)
    
    # Check content type to determine if JSON or FormData
    content_type = request.headers.get("content-type", "").lower()
    is_json = "application/json" in content_type
    is_multipart = "multipart/form-data" in content_type
    
    tenant_request = None
    logo_file = None
    
    if is_json:
        # Handle JSON request
        try:
            json_data = await request.json()
            tenant_request = TenantRequest(**json_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON data: {str(e)}"
            )
    elif is_multipart:
        # Handle FormData request
        try:
            form_data = await request.form()
            
            # Extract form fields
            name = form_data.get("name")
            category = form_data.get("category")
            domain = form_data.get("domain")
            database_name = form_data.get("database_name")
            is_active = form_data.get("is_active")
            admin_username = form_data.get("admin_username")
            admin_password = form_data.get("admin_password")
            must_change_password = form_data.get("must_change_password")
            
            # Get logo file if provided
            if "logo" in form_data:
                file_value = form_data["logo"]
                # Check if it's an UploadFile object (has filename attribute)
                if hasattr(file_value, 'filename') and file_value.filename:
                    logo_file = file_value
            
            # Handle boolean conversion for Form fields
            is_active_bool = None
            if is_active is not None:
                if isinstance(is_active, str):
                    if is_active.strip():
                        is_active_bool = is_active.lower() in ('true', '1', 'yes', 'on')
                else:
                    is_active_bool = bool(is_active)
            
            must_change_password_bool = None
            if must_change_password is not None:
                if isinstance(must_change_password, str):
                    if must_change_password.strip():
                        must_change_password_bool = must_change_password.lower() in ('true', '1', 'yes', 'on')
                else:
                    must_change_password_bool = bool(must_change_password)
            
            # Create TenantRequest object
            tenant_request = TenantRequest(
                name=name if name else "",
                category=category.upper() if category else "HI",
                domain=domain if domain and str(domain).strip() else None,
                database_name=database_name if database_name and str(database_name).strip() else None,
                is_active=is_active_bool,
                admin_username=admin_username if admin_username and str(admin_username).strip() else None,
                admin_password=admin_password if admin_password and str(admin_password).strip() else None,
                must_change_password=must_change_password_bool if must_change_password_bool is not None else False
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid form data: {str(e)}"
            )
    else:
        # Try to parse as JSON if content type is not specified
        try:
            body_bytes = await request.body()
            if body_bytes:
                json_data = json.loads(body_bytes.decode('utf-8'))
                tenant_request = TenantRequest(**json_data)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body is required"
                )
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content-Type must be either 'application/json' or 'multipart/form-data'. Error: {str(e)}"
            )
    
    if not tenant_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request data"
        )
    
    try:
        return await create_new_tenant(db=db, tenant=tenant_request, logo_file=logo_file)
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

@tenant.get("/tenants/me", response_model=TenantResponse)
async def get_my_tenant(
    x_tenant_name: Optional[str] = Header(default=None, alias="X-Tenant-Name"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's tenant information.
    Accessible to all authenticated users - returns their own tenant based on user's institution_id.
    Falls back to X-Tenant-Name header if institution_id is not available.
    """
    # System admins don't have a tenant
    is_system_admin = current_user.role and current_user.role.startswith('system_')
    if is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System admins do not belong to a tenant"
        )
    
    tenant = None
    
    # Priority 1: Use institution_id to get tenant by ID (most reliable)
    if current_user.institution_id:
        try:
            tenant = get_tenant_by_id(db, current_user.institution_id)
        except Exception as e:
            # If tenant not found by ID, continue to fallback methods
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Tenant not found by institution_id {current_user.institution_id}: {e}")
    
    # Priority 2: Use tenant name from header
    if not tenant and x_tenant_name:
        tenant = get_tenant_by_name(db, x_tenant_name)
    
    # Priority 3: Try to get tenant name from user attributes
    if not tenant:
        tenant_name = getattr(current_user, 'tenant_name', None) or \
                     getattr(current_user, 'tenantName', None) or \
                     getattr(current_user, 'domain', None)
        if tenant_name:
            tenant = get_tenant_by_name(db, tenant_name)
    
    if not tenant:
        from app.exceptions import NotFoundError
        raise NotFoundError(
            f"Tenant not found. User institution_id: {current_user.institution_id}, "
            f"X-Tenant-Name header: {x_tenant_name}"
        )
    
    # Convert SQLAlchemy model to Pydantic response model
    return TenantResponse.model_validate(tenant, from_attributes=True)

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
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update a tenant (requires system admin role)
    
    Accepts both JSON and multipart/form-data:
    
    JSON Request (Content-Type: application/json):
    {
        "name": "string",
        "category": "HI" | "SI",
        "domain": "string",
        "is_active": true/false,
        "admin_username": "string",
        "admin_password": "string",
        "must_change_password": true/false
    }
    
    FormData Request (Content-Type: multipart/form-data):
    - name: Optional tenant name
    - category: Optional category (HI or SI)
    - domain: Optional tenant domain
    - is_active: Optional active status (true/false string)
    - admin_username: Optional admin username
    - admin_password: Optional admin password
    - must_change_password: Optional flag (true/false string)
    - logo: Optional logo file upload
    
    Note: All fields are optional. Only provided fields will be updated.
    """
    check_system_admin(current_user)
    
    # Check content type to determine if JSON or FormData
    content_type = request.headers.get("content-type", "").lower()
    is_json = "application/json" in content_type
    is_multipart = "multipart/form-data" in content_type
    
    tenant_update = None
    logo_file = None
    
    if is_json:
        # Handle JSON request
        print("Handling JSON request for tenant update...")
        try:
            json_data = await request.json()
            print(f"Received JSON data: {json_data}")
            tenant_update = TenantUpdate(**json_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON data: {str(e)}"
            )
    
    elif is_multipart:
        # Handle FormData request
        try:
            form_data = await request.form()
            
            # Extract form fields
            name = form_data.get("name")
            category = form_data.get("category")
            domain = form_data.get("domain")
            is_active = form_data.get("is_active")
            admin_username = form_data.get("admin_username")
            admin_password = form_data.get("admin_password")
            must_change_password = form_data.get("must_change_password")
            # Get logo file if provided
            logo_file = None
            if "logo" in form_data:
                file_value = form_data["logo"]
                # Check if it's an UploadFile object (has filename attribute)
                if hasattr(file_value, 'filename') and file_value.filename:
                    logo_file = file_value
            
            # Handle boolean conversion for Form fields
            is_active_bool = None
            if is_active is not None:
                if isinstance(is_active, str):
                    if is_active.strip():
                        is_active_bool = is_active.lower() in ('true', '1', 'yes', 'on')
                else:
                    is_active_bool = bool(is_active)
            
            must_change_password_bool = None
            if must_change_password is not None:
                if isinstance(must_change_password, str):
                    if must_change_password.strip():
                        must_change_password_bool = must_change_password.lower() in ('true', '1', 'yes', 'on')
                else:
                    must_change_password_bool = bool(must_change_password)
            
            # Only set fields that are not None and not empty strings
            tenant_update = TenantUpdate(
                name=name if name and str(name).strip() else None,
                category=category if category and str(category).strip() else None,
                domain=domain if domain and str(domain).strip() else None,
                is_active=is_active_bool,
                admin_username=admin_username if admin_username and str(admin_username).strip() else None,
                admin_password=admin_password if admin_password and str(admin_password).strip() else None,
                must_change_password=must_change_password_bool
            )
           
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid form data: {str(e)}"
            )
        print("OK LET US PROCEED. TO ELSE PART....")
    else:
        # Try to parse as JSON if content type is not specified
        try:
            # Check if there's a body
            body_bytes = await request.body()
            if body_bytes:
                # Try to parse as JSON
                json_data = json.loads(body_bytes.decode('utf-8'))
                tenant_update = TenantUpdate(**json_data)
            else:
                # Empty body, create empty TenantUpdate
                tenant_update = TenantUpdate()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content-Type must be either 'application/json' or 'multipart/form-data'. Error: {str(e)}"
            )
    
    # Ensure tenant_update is set
    if tenant_update is None:
        tenant_update = TenantUpdate()
        
    # Update tenant
    updated_tenant = await update_tenant(
        db=db, 
        tenant_id=tenant_id, 
        tenant_update=tenant_update,
        logo_file=logo_file
    )
    
    return updated_tenant

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
