from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from app.schemas.tenant_settings import TenantSettings, TenantSettingsRequest, TenantSettingsResponse
from app.apis.tenant_settings import (
    get_tenant_category,
    get_tenant_settings,
    create_or_update_tenant_settings,
    is_matricule_format_configured,
    preview_student_id
)
from app.apis.students import resolve_student_for_logged_in_user
from app.models.student_service_usage import StudentServiceUsage
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from typing import Optional

tenant_settings_router = APIRouter()

@tenant_settings_router.get("/tenant-settings", response_model=TenantSettingsResponse)
def get_settings(
    institution_id: int = Query(None, description="Institution ID (optional, for system admins only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get tenant settings for current user's institution"""
    # Use institution_id from query param if provided (system admin), otherwise from current user
    target_institution_id = institution_id or current_user.institution_id
    
    if not target_institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to access tenant settings"
        )
    
    # Verify permission: non-system admins can only view their own institution
    if institution_id and institution_id != current_user.institution_id:
        if not current_user.role or 'system_' not in current_user.role.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own institution's settings"
            )
    
    institution_id = target_institution_id
    print("INSTITUTION ID FROM CLIENT ", institution_id)
    category = get_tenant_category(db, institution_id)
    settings = get_tenant_settings(db, institution_id)
    print("INSTITUTION ID FROM SERVER ", category.category)
    if not settings or not category:
        # Return default response if no settings exist
        from app.constants.program_levels import DEFAULT_ENABLED_PROGRAM_LEVELS

        return TenantSettingsResponse(
            id=0,
            institution_id=institution_id,
            matricule_format=None,
            branches_enabled=False,
            current_semester_id=None,
            enabled_program_levels=list(DEFAULT_ENABLED_PROGRAM_LEVELS),
        )
    
    # model_validator will handle JSON string parsing automatically
     
#     return TenantSettingsResponse.model_validate({
#      **settings.__dict__,   # unpack settings fields
#     "category": category.category  # add category from tenant
# })
    settings_model = TenantSettings.model_validate(settings)

    return TenantSettingsResponse(
        **settings_model.model_dump(),
        category=category.category
    )

@tenant_settings_router.put("/tenant-settings", response_model=TenantSettingsResponse)
def update_settings(
    settings: TenantSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update tenant settings (requires admin role)"""
    # Use institution_id from request body if provided, otherwise extract from current user
    institution_id = settings.institution_id or current_user.institution_id
    
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to update tenant settings"
        )
    
    # If institution_id was provided in body, verify it matches current user's institution (or user is system admin)
    if settings.institution_id and settings.institution_id != current_user.institution_id:
        # Only system admins can update other institutions' settings
        if not current_user.role or 'system_' not in current_user.role.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own institution's settings"
            )
    
    # Create request without institution_id in body (we use it for lookup only)
    settings_without_institution_id = TenantSettingsRequest(
        matricule_format=settings.matricule_format,
        email_reminder_time=settings.email_reminder_time,
        branches_enabled=settings.branches_enabled,
        payroll_auto_generate_codes=settings.payroll_auto_generate_codes,
        current_semester_id=settings.current_semester_id,
        enabled_program_levels=settings.enabled_program_levels,
    )
    
    updated_settings = create_or_update_tenant_settings(db, institution_id, settings_without_institution_id)
    category = get_tenant_category(db, institution_id)
    settings_model = TenantSettings.model_validate(updated_settings)
    return TenantSettingsResponse(
        **settings_model.model_dump(),
        category=(category.category if category else "school"),
    )

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


@tenant_settings_router.post("/tenant-settings/preview-matricule")
def preview_matricule(
    preview_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Preview student matricule number based on configured format and provided data.
    Does NOT increment any sequence counters.
    """
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    try:
        matricule = preview_student_id(db, institution_id, preview_data)
        return {"matricule": matricule}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tenant_settings_router.post("/tenant-settings/allocate-student-matricule")
def allocate_student_matricule(
    student_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Allocate and return the next student ID (matricule).
    This RESERVES the matricule by incrementing the sequence.
    Use this to hold a matricule temporarily until the student is saved.
    """
    from app.apis.tenant_settings import allocate_student_matricule as allocate_fn
    
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    try:
        matricule = allocate_fn(db, institution_id, student_data)
        return {"matricule": matricule, "allocated": True}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tenant_settings_router.post("/tenant-settings/allocate-lecturer-matricule")
def allocate_lecturer_matricule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Allocate and return the next lecturer employee_id (matricule).
    This reserves the matricule temporarily. If not used within the session,
    the sequence will be used on the next call (not rolled back).
    For actual saving, the lecturer creation API will allocate its own.
    This is a preview/hold mechanism for UI display.
    """
    from app.apis.tenant_settings import allocate_next_lecturer_employee_id
    
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    try:
        # This actually allocates and increments the sequence
        matricule = allocate_next_lecturer_employee_id(db, institution_id)
        return {"matricule": matricule, "allocated": True}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tenant_settings_router.post("/tenant-settings/service-usage/increment")
def increment_service_usage(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    """
    Increment per-student usage count for monetized/freemium service actions.
    Stores usage in DB so free-limit checks are durable across devices/sessions.
    """
    service_key = str(payload.get("service_key") or "").strip()
    if not service_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="service_key is required")

    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    row = (
        db.query(StudentServiceUsage)
        .filter(
            StudentServiceUsage.institution_id == student.institution_id,
            StudentServiceUsage.student_id == student.id,
            StudentServiceUsage.service_key == service_key,
        )
        .first()
    )
    if row:
        row.usage_count = int(row.usage_count or 0) + 1
    else:
        row = StudentServiceUsage(
            institution_id=student.institution_id,
            student_id=student.id,
            service_key=service_key,
            usage_count=1,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"service_key": service_key, "usage_count": int(row.usage_count or 0)}
