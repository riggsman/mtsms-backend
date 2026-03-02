from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.database.base import get_db_session
from app.database.sessionManager import get_database_mode, set_database_mode
from app.models.system_config import SystemConfig
from app.schemas.system_config import (
    DatabaseModeResponse,
    DatabaseModeUpdate,
    SystemConfigResponse,
    SystemConfigUpdate,
    NotificationAdminEmailsConfig,
)
from app.dependencies.auth import get_current_user, require_any_role_admin
from app.models.user import User
from app.models.role import UserRole
from app.conf.config import settings

system_config = APIRouter()

@system_config.get("/database-mode", response_model=DatabaseModeResponse, tags=["System Config"])
def get_database_mode_endpoint(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current database architecture mode.
    Only accessible by super_admin.
    """
    # Check if user is super_admin or system_super_admin
    if (current_user.role != UserRole.SUPER_ADMIN.value and 
        not (current_user.role and current_user.role.startswith('system_'))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin or system_super_admin can access system configuration"
        )
    
    mode = get_database_mode()
    description = (
        "All tenants share a single database. Data is separated by tenant_id fields."
        if mode == 'shared' 
        else "Each tenant has its own separate database."
    )
    
    return DatabaseModeResponse(mode=mode, description=description)


@system_config.put("/database-mode", response_model=DatabaseModeResponse, tags=["System Config"])
def update_database_mode_endpoint(
    mode_update: DatabaseModeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Update the database architecture mode.
    Only accessible by super_admin.
    
    WARNING: Changing modes may require data migration!
    """
    # Check if user is super_admin
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can update system configuration"
        )
    
    # Validate mode
    if mode_update.mode not in ['shared', 'multi_tenant']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'shared' or 'multi_tenant'"
        )
    
    try:
        set_database_mode(mode_update.mode, db)
        description = (
            "All tenants share a single database. Data is separated by tenant_id fields."
            if mode_update.mode == 'shared' 
            else "Each tenant has its own separate database."
        )
        
        return DatabaseModeResponse(mode=mode_update.mode, description=description)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update database mode: {str(e)}"
        )


@system_config.get("/config/{key}", response_model=SystemConfigResponse, tags=["System Config"])
def get_system_config(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Get a system configuration value by key.
    Only accessible by super_admin.
    """
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can access system configuration"
        )
    
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    return config


@system_config.put("/config/{key}", response_model=SystemConfigResponse, tags=["System Config"])
def update_system_config(
    key: str,
    config_update: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Update a system configuration value.
    Only accessible by super_admin.
    """
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super_admin can update system configuration"
        )
    
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    if config_update.value is not None:
        config.value = config_update.value
    if config_update.description is not None:
        config.description = config_update.description
    
    db.commit()
    db.refresh(config)
    
    return config


def _get_notification_admin_emails_from_env() -> NotificationAdminEmailsConfig:
    """
    Build notification admin emails config from environment variable
    as a fallback when not configured in the database.
    """
    emails = settings.system_admin_notification_emails
    return NotificationAdminEmailsConfig(
        emails=[
            # enabled by default when coming from env
            # validation of email format is handled by NotificationAdminEmail
            {"email": email, "enabled": True}
            for email in emails
        ]
    )


def _get_notification_admin_config_from_db(
    db: Session,
) -> Optional[NotificationAdminEmailsConfig]:
    config = db.query(SystemConfig).filter(
        SystemConfig.key == "notification_admin_emails"
    ).first()
    if not config or not config.value:
        return None

    try:
        raw = json.loads(config.value)
        return NotificationAdminEmailsConfig.model_validate(raw)
    except Exception:
        # If stored JSON is invalid, ignore and fall back to env
        return None


@system_config.get(
    "/notification-admin-emails",
    response_model=NotificationAdminEmailsConfig,
    tags=["System Config"],
)
def get_notification_admin_emails(
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.SUPER_ADMIN,
            UserRole.SECRETARY,
        )
    ),
    db: Session = Depends(get_db_session),
):
    """
    Get system admin notification emails.

    - Returns DB configuration if present and valid.
    - Otherwise falls back to `.env` variable `SYSTEM_ADMIN_NOTIFICATION_EMAILS`.
    - Maximum of 3 emails, each with an `enabled` flag.
    """
    config = _get_notification_admin_config_from_db(db)
    if config:
        return config

    # Fallback to environment configuration
    return _get_notification_admin_emails_from_env()


@system_config.put(
    "/notification-admin-emails",
    response_model=NotificationAdminEmailsConfig,
    tags=["System Config"],
)
def update_notification_admin_emails(
    payload: NotificationAdminEmailsConfig,
    current_user: User = Depends(
        require_any_role_admin(
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.SUPER_ADMIN,
            UserRole.SECRETARY,
        )
    ),
    db: Session = Depends(get_db_session),
):
    """
    Update system admin notification emails.

    - Allows configuring up to 3 emails.
    - Each email can be marked `enabled` to receive notifications.
    """
    # Payload validator already enforces max 3 and email format.
    # Persist as JSON in SystemConfig.
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.key == "notification_admin_emails"
        ).first()

        if not config:
            config = SystemConfig(
                key="notification_admin_emails",
                description=(
                    "List of system admin emails (max 3) that can receive system notifications. "
                    "Each email has an enabled flag."
                ),
            )
            db.add(config)

        # Serialize payload to JSON string
        import json
        config.value = json.dumps(payload.model_dump(), ensure_ascii=False)
        
        db.commit()
        db.refresh(config)
        
        # Verify the save by reading it back
        db.refresh(config)
        if not config.value:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save notification admin emails configuration"
            )
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save notification admin emails: {str(e)}"
        )

    return payload
