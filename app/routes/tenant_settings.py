from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.tenant_settings import TenantSettingsRequest, TenantSettingsResponse
from app.apis.tenant_settings import (
    get_tenant_settings,
    create_or_update_tenant_settings,
    is_matricule_format_configured
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole

tenant_settings_router = APIRouter()

@tenant_settings_router.get("/tenant-settings", response_model=TenantSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get tenant settings for current user's institution"""
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to access tenant settings"
        )
    
    settings = get_tenant_settings(db, institution_id)
    if not settings:
        # Return default response if no settings exist
        return TenantSettingsResponse(
            id=0,
            institution_id=institution_id,
            matricule_format=None
        )
    
    # model_validator will handle JSON string parsing automatically
    return TenantSettingsResponse.model_validate(settings)

@tenant_settings_router.put("/tenant-settings", response_model=TenantSettingsResponse)
def update_settings(
    settings: TenantSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update tenant settings (requires admin role)"""
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to update tenant settings"
        )
    
    updated_settings = create_or_update_tenant_settings(db, institution_id, settings)
    # model_validator will handle JSON string parsing automatically
    return TenantSettingsResponse.model_validate(updated_settings)

@tenant_settings_router.get("/tenant-settings/status")
def get_settings_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Check if matricule format is configured (for UI warnings)"""
    institution_id = current_user.institution_id
    if not institution_id:
        return {"is_configured": False, "message": "User must belong to an institution"}
    
    is_configured = is_matricule_format_configured(db, institution_id)
    return {
        "is_configured": is_configured,
        "message": "Matricule format is configured" if is_configured else "Matricule format is not configured"
    }
