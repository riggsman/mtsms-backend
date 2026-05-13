"""
System Settings API Routes

This router handles global system-level settings including Firebase Messaging configuration.

To use this router in your main FastAPI app, include it like this:

    from app.routes.system_settings import system_settings_router
    
    app.include_router(system_settings_router, prefix="/api/v1")

The endpoints will be available at:
    GET  /api/v1/system/settings
    PUT  /api/v1/system/settings
    POST /api/v1/system/logo
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.models.role import UserRole
from app.dependencies.auth import get_current_user
from app.helpers.user_roles import user_is_system_admin
from app.schemas.system_settings import (
    SystemSettingsRequest,
    SystemSettingsResponse,
    SystemSettingsState,
    FirebaseMessagingConfig,
    FirebaseWebClientBundle,
    FirebaseWebAppConfig,
)


system_settings = APIRouter()


def get_firebase_config_from_db_or_env(db: Session):
    """Get Firebase config from database, with env var fallback."""
    settings: Optional[SystemSettings] = (
        db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    )
    
    import os
    
    firebase_enabled = settings.firebase_messaging_enabled if settings else False
    firebase_api_key = settings.firebase_api_key if settings else None
    firebase_auth_domain = settings.firebase_auth_domain if settings else None
    firebase_project_id = settings.firebase_project_id if settings else None
    firebase_messaging_sender_id = settings.firebase_messaging_sender_id if settings else None
    firebase_app_id = settings.firebase_app_id if settings else None
    firebase_storage_bucket = settings.firebase_storage_bucket if settings else None
    firebase_measurement_id = settings.firebase_measurement_id if settings else None
    firebase_vapid_key = settings.firebase_vapid_key if settings else None
    
    if not firebase_enabled and os.getenv("FIREBASE_MESSAGING_ENABLED", "").lower() == "true":
        firebase_enabled = True
    if not firebase_api_key:
        firebase_api_key = os.getenv("FIREBASE_API_KEY")
    if not firebase_auth_domain:
        firebase_auth_domain = os.getenv("FIREBASE_AUTH_DOMAIN", f"{firebase_project_id}.firebaseapp.com" if firebase_project_id else None)
    if not firebase_project_id:
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not firebase_messaging_sender_id:
        firebase_messaging_sender_id = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
    if not firebase_app_id:
        firebase_app_id = os.getenv("FIREBASE_APP_ID")
    if not firebase_vapid_key:
        firebase_vapid_key = os.getenv("FIREBASE_VAPID_KEY")
    
    return {
        "enabled": firebase_enabled,
        "apiKey": firebase_api_key,
        "authDomain": firebase_auth_domain,
        "projectId": firebase_project_id,
        "messagingSenderId": firebase_messaging_sender_id,
        "appId": firebase_app_id,
        "storageBucket": firebase_storage_bucket,
        "measurementId": firebase_measurement_id,
        "vapidKey": firebase_vapid_key,
    }


@system_settings.get(
    "/system/firebase-web-config",
    response_model=FirebaseWebClientBundle,
    tags=["System Settings"],
)
def get_firebase_web_config(
    db: Session = Depends(get_db_session),
):
    """
    Public endpoint to serve Firebase web config for browser FCM initialization.
    Returns only what's needed for getToken() in the browser - no auth required.
    Falls back to environment variables if database config is incomplete.
    """
    config = get_firebase_config_from_db_or_env(db)
    
    if not config["enabled"]:
        return FirebaseWebClientBundle(enabled=False, web=None, vapidKey=None)
    
    if not all([
        config["apiKey"],
        config["authDomain"],
        config["projectId"],
        config["messagingSenderId"],
        config["appId"],
    ]):
        return FirebaseWebClientBundle(enabled=False, web=None, vapidKey=None)
    
    web_config = FirebaseWebAppConfig(
        apiKey=config["apiKey"],
        authDomain=config["authDomain"],
        projectId=config["projectId"],
        messagingSenderId=config["messagingSenderId"],
        appId=config["appId"],
        storageBucket=config["storageBucket"],
        measurementId=config["measurementId"],
    )
    
    return FirebaseWebClientBundle(
        enabled=True,
        web=web_config,
        vapidKey=config["vapidKey"],
    )


@system_settings.get(
    "/system/cache-version",
    tags=["System Settings"],
)
def get_cache_version(
    db: Session = Depends(get_db_session),
):
    """
    Get the current cache version for frontend cache synchronization.
    """
    settings: Optional[SystemSettings] = (
        db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    )
    return {"cache_version": settings.cache_version if settings else "1"}


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
    
    if settings is None:
        return SystemSettingsState(
            maintenanceMode=False,
            allowNewRegistrations=True,
            emailNotifications=True,
            cacheTimeout=5,
            inactivityTimeout=5,
            maintenanceCheckInterval=60,
        )
    
    return SystemSettingsState(
        maintenanceMode=settings.maintenance_mode,
        allowNewRegistrations=settings.allow_new_registrations,
        emailNotifications=settings.email_notifications,
        cacheTimeout=getattr(settings, "cache_timeout", 5),
        inactivityTimeout=getattr(settings, "inactivity_timeout", 5),
        maintenanceCheckInterval=getattr(settings, "maintenance_check_interval", 60),
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
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can access system settings"
        )

    import os

    settings = _get_or_create_singleton(db)

    firebase_cfg: Optional[FirebaseMessagingConfig] = None
    
    fb_enabled = settings.firebase_messaging_enabled if settings else False
    fb_api_key = settings.firebase_api_key if settings else None
    fb_auth_domain = settings.firebase_auth_domain if settings else None
    fb_project_id = settings.firebase_project_id if settings else None
    fb_sender_id = settings.firebase_messaging_sender_id if settings else None
    fb_app_id = settings.firebase_app_id if settings else None
    fb_vapid_key = settings.firebase_vapid_key if settings else None
    fb_storage_bucket = settings.firebase_storage_bucket if settings else None
    fb_measurement_id = settings.firebase_measurement_id if settings else None
    
    if not fb_enabled and os.getenv("FIREBASE_MESSAGING_ENABLED", "").lower() == "true":
        fb_enabled = True
    if not fb_api_key:
        fb_api_key = os.getenv("FIREBASE_API_KEY")
    if not fb_auth_domain:
        fb_auth_domain = os.getenv("FIREBASE_AUTH_DOMAIN")
    if not fb_project_id:
        fb_project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not fb_sender_id:
        fb_sender_id = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
    if not fb_app_id:
        fb_app_id = os.getenv("FIREBASE_APP_ID")
    if not fb_vapid_key:
        fb_vapid_key = os.getenv("FIREBASE_VAPID_KEY")
    
    if fb_enabled or any([fb_api_key, fb_auth_domain, fb_project_id, fb_sender_id, fb_app_id, fb_vapid_key]):
        firebase_cfg = FirebaseMessagingConfig(
            enabled=fb_enabled,
            apiKey=fb_api_key,
            authDomain=fb_auth_domain,
            projectId=fb_project_id,
            messagingSenderId=fb_sender_id,
            appId=fb_app_id,
            vapidKey=fb_vapid_key,
            storageBucket=fb_storage_bucket,
            measurementId=fb_measurement_id,
            serviceAccountUploaded=settings.firebase_service_account_uploaded if settings else False,
        )

    return SystemSettingsResponse(
        id=settings.id,
        maintenanceMode=settings.maintenance_mode,
        allowNewRegistrations=settings.allow_new_registrations,
        maxTenants=settings.max_tenants,
        sessionTimeout=settings.session_timeout,
        emailNotifications=settings.email_notifications,
        cacheTimeout=getattr(settings, "cache_timeout", 5),
        inactivityTimeout=getattr(settings, "inactivity_timeout", 5),
        maintenanceCheckInterval=getattr(settings, "maintenance_check_interval", 60),
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
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can update system settings"
        )

    settings = _get_or_create_singleton(db)

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
    if payload.cacheTimeout is not None:
        settings.cache_timeout = payload.cacheTimeout
    if payload.inactivityTimeout is not None:
        settings.inactivity_timeout = payload.inactivityTimeout
    if payload.maintenanceCheckInterval is not None:
        settings.maintenance_check_interval = payload.maintenanceCheckInterval

    if payload.firebaseMessaging is not None:
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

    try:
        db.add(settings)
        db.commit()
        db.refresh(settings)
        
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
            storageBucket=settings.firebase_storage_bucket,
            measurementId=settings.firebase_measurement_id,
            serviceAccountUploaded=settings.firebase_service_account_uploaded,
        )

    return SystemSettingsResponse(
        id=settings.id,
        maintenanceMode=settings.maintenance_mode,
        allowNewRegistrations=settings.allow_new_registrations,
        maxTenants=settings.max_tenants,
        sessionTimeout=settings.session_timeout,
        emailNotifications=settings.email_notifications,
        cacheTimeout=getattr(settings, "cache_timeout", 5),
        inactivityTimeout=getattr(settings, "inactivity_timeout", 5),
        maintenanceCheckInterval=getattr(settings, "maintenance_check_interval", 60),
        firebaseMessaging=firebase_cfg,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@system_settings.post(
    "/system/logo",
    tags=["System Settings"],
)
async def upload_system_logo(
    logo: Optional[UploadFile] = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload system logo (system admin only).
    Accepts a logo file and stores the URL in system_settings.
    """
    from app.helpers.file_upload import save_uploaded_file, delete_file, get_file_url
    
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin can upload system logo"
        )

    settings = _get_or_create_singleton(db)

    if logo:
        allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml', 'image/webp'}
        content_type = logo.content_type or ''
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )

        old_logo_path = settings.logo_url
        if old_logo_path:
            try:
                delete_file(old_logo_path)
            except Exception as e:
                print(f"Warning: Could not delete old logo: {e}")

        file_path, relative_path = await save_uploaded_file(
            file=logo,
            tenant_domain='system',
            file_category='logo'
        )

        logo_url = get_file_url(relative_path, base_url="/api/v1/uploads")
        settings.logo_url = logo_url

        try:
            db.commit()
            db.refresh(settings)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save logo: {str(e)}"
            )

        return {"logo": logo_url, "logo_url": logo_url}

    return {"logo": settings.logo_url, "logo_url": settings.logo_url}

