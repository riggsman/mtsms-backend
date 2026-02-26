from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.base import get_db_session
from app.database.sessionManager import get_database_mode, set_database_mode
from app.models.system_config import SystemConfig
from app.schemas.system_config import (
    DatabaseModeResponse,
    DatabaseModeUpdate,
    SystemConfigResponse,
    SystemConfigUpdate
)
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.role import UserRole

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
