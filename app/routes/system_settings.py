"""
System Settings API Routes

This router handles global system-level settings including Firebase Messaging configuration.

To use this router in your main FastAPI app, include it like this:

    from app.routes.system_settings import system_settings_router
    
    app.include_router(system_settings_router, prefix="/api/v1")

The endpoints will be available at:
    GET  /api/v1/system/settings
    PUT  /api/v1/system/settings
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.models.role import UserRole
from app.dependencies.auth import get_current_user
from app.schemas.system_settings import (
    SystemSettingsRequest,
    SystemSettingsResponse,
    SystemSettingsState,
    FirebaseMessagingConfig,
)


system_settings = APIRouter()


@system_settings.get(
    "/system/maintenance-mode",
    tags=["System Settings"],
)
def get_maintenance_mode(
    db: Session = Depends(get_db_session),
):
    """
    Get maintenance mode status (public endpoint).
    Returns whether the system is currently in maintenance mode.
    No authentication required - safe for public use.
    """
    settings: Optional[SystemSettings] = (
        db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    )
    
    # If no settings exist, return default (not in maintenance)
    maintenance_mode = settings.maintenance_mode if settings else False
    
    return {"maintenanceMode": maintenance_mode}


@system_settings.get(
    "/system/settings/state",
    response_model=SystemSettingsState,
    tags=["System Settings"],
)
def get_system_settings_state(
    db: Session = Depends(get_db_session),
):
    """
    Get essential system settings state (public endpoint).
    Returns maintenance mode and other critical settings that the frontend needs to check.
    No authentication required - safe for public use.
    """
    settings: Optional[SystemSettings] = (
        db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    )
    
    # If no settings exist, return defaults
    if settings is None:
        return SystemSettingsState(
            maintenanceMode=False,
            allowNewRegistrations=True,
            emailNotifications=True,
        )
    
    return SystemSettingsState(
        maintenanceMode=settings.maintenance_mode,
        allowNewRegistrations=settings.allow_new_registrations,
        emailNotifications=settings.email_notifications,
    )


def _get_or_create_singleton(db: Session) -> SystemSettings:
    """
    Fetch the single SystemSettings row, creating it with defaults if missing.
    """
    settings: Optional[SystemSettings] = (
        db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    )
    if settings is None:
        try:
            settings = SystemSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        except Exception as e:
            db.rollback()
            # If creation fails, try to fetch again (might have been created by another request)
            settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
            if settings is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create system settings: {str(e)}"
                )
    return settings


@system_settings.get(
    "/system/settings",
    response_model=SystemSettingsResponse,
)
def get_system_settings(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Return global system settings for the platform (system admin only).
    """
    # Check if user is system admin or system super admin
    if (current_user.role != UserRole.SYSTEM_ADMIN.value and 
        current_user.role != UserRole.SYSTEM_SUPER_ADMIN.value and
        not (current_user.role and current_user.role.startswith('system_'))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can access system settings"
        )

    settings = _get_or_create_singleton(db)

    # Build Firebase config from individual columns
    firebase_cfg: Optional[FirebaseMessagingConfig] = None
    if settings.firebase_messaging_enabled or any([
        settings.firebase_api_key,
        settings.firebase_auth_domain,
        settings.firebase_project_id,
        settings.firebase_messaging_sender_id,
        settings.firebase_app_id,
        settings.firebase_vapid_key,
    ]):
        firebase_cfg = FirebaseMessagingConfig(
            enabled=settings.firebase_messaging_enabled,
            apiKey=settings.firebase_api_key,
            authDomain=settings.firebase_auth_domain,
            projectId=settings.firebase_project_id,
            messagingSenderId=settings.firebase_messaging_sender_id,
            appId=settings.firebase_app_id,
            vapidKey=settings.firebase_vapid_key,
        )

    return SystemSettingsResponse(
        id=settings.id,
        maintenanceMode=settings.maintenance_mode,
        allowNewRegistrations=settings.allow_new_registrations,
        maxTenants=settings.max_tenants,
        sessionTimeout=settings.session_timeout,
        emailNotifications=settings.email_notifications,
        firebaseMessaging=firebase_cfg,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@system_settings.put(
    "/system/settings",
    response_model=SystemSettingsResponse,
)
def update_system_settings(
    payload: SystemSettingsRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update global system settings from the admin UI.
    Only fields provided in the payload are updated (partial update).
    """
    # Check if user is system admin or system super admin
    if (current_user.role != UserRole.SYSTEM_ADMIN.value and 
        current_user.role != UserRole.SYSTEM_SUPER_ADMIN.value and
        not (current_user.role and current_user.role.startswith('system_'))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can update system settings"
        )

    settings = _get_or_create_singleton(db)

    # Map camelCase payload fields to snake_case model attributes
    if payload.maintenanceMode is not None:
        settings.maintenance_mode = payload.maintenanceMode
    if payload.allowNewRegistrations is not None:
        settings.allow_new_registrations = payload.allowNewRegistrations
    if payload.maxTenants is not None:
        settings.max_tenants = payload.maxTenants
    if payload.sessionTimeout is not None:
        settings.session_timeout = payload.sessionTimeout
    if payload.emailNotifications is not None:
        settings.email_notifications = payload.emailNotifications

    if payload.firebaseMessaging is not None:
        # Update individual Firebase config columns
        fm = payload.firebaseMessaging
        if fm.enabled is not None:
            settings.firebase_messaging_enabled = fm.enabled
        if fm.apiKey is not None:
            settings.firebase_api_key = fm.apiKey
        if fm.authDomain is not None:
            settings.firebase_auth_domain = fm.authDomain
        if fm.projectId is not None:
            settings.firebase_project_id = fm.projectId
        if fm.messagingSenderId is not None:
            settings.firebase_messaging_sender_id = fm.messagingSenderId
        if fm.appId is not None:
            settings.firebase_app_id = fm.appId
        if fm.vapidKey is not None:
            settings.firebase_vapid_key = fm.vapidKey

    # Since settings was retrieved from DB, it's already tracked - no need for db.add()
    # Just commit the changes
    try:
        db.add(settings)  # Optional, can be omitted since settings is already in the session
        db.commit()
        db.refresh(settings)
        
        # Verify the save by checking if updated_at changed
        if settings.updated_at is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save system settings: updated_at was not set"
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save system settings: {str(e)}"
        )

    # Build Firebase config from individual columns for response
    firebase_cfg: Optional[FirebaseMessagingConfig] = None
    if settings.firebase_messaging_enabled or any([
        settings.firebase_api_key,
        settings.firebase_auth_domain,
        settings.firebase_project_id,
        settings.firebase_messaging_sender_id,
        settings.firebase_app_id,
        settings.firebase_vapid_key,
    ]):
        firebase_cfg = FirebaseMessagingConfig(
            enabled=settings.firebase_messaging_enabled,
            apiKey=settings.firebase_api_key,
            authDomain=settings.firebase_auth_domain,
            projectId=settings.firebase_project_id,
            messagingSenderId=settings.firebase_messaging_sender_id,
            appId=settings.firebase_app_id,
            vapidKey=settings.firebase_vapid_key,
        )

    return SystemSettingsResponse(
        id=settings.id,
        maintenanceMode=settings.maintenance_mode,
        allowNewRegistrations=settings.allow_new_registrations,
        maxTenants=settings.max_tenants,
        sessionTimeout=settings.session_timeout,
        emailNotifications=settings.email_notifications,
        firebaseMessaging=firebase_cfg,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )

