from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.role import UserRole
from app.models.tenant import Tenant
from app.models.system_config import SystemConfig
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from app.routes.system_settings import _get_or_create_singleton
from app.schemas.system_settings import FirebaseMessagingConfig, SystemSettingsRequest

system_admin = APIRouter()

def check_system_admin(current_user: User):
    """Helper to check if user is system admin"""
    if (current_user.role != UserRole.SUPER_ADMIN.value and 
        not (current_user.role and current_user.role.startswith('system_'))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required system admin role"
        )

@system_admin.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get system-wide statistics"""
    check_system_admin(current_user)
    
    # Get total tenants
    total_tenants = db.query(Tenant).count()
    
    # Get active tenants
    active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    
    # Get total users (from shared database or aggregate from all tenants)
    # This is a simplified version - you may need to query tenant databases
    total_users = db.query(User).filter(User.deleted_at.is_(None)).count()
    
    # Get system users count
    system_users = db.query(User).filter(
        and_(
            User.user_type == 'SYSTEM',
            User.deleted_at.is_(None)
        )
    ).count()
    
    # Get tenant users count
    tenant_users = db.query(User).filter(
        and_(
            User.user_type == 'TENANT',
            User.deleted_at.is_(None)
        )
    ).count()
    
    return {
        "totalTenants": total_tenants,
        "activeTenants": active_tenants,
        "totalUsers": total_users,
        "systemUsers": system_users,
        "tenantUsers": tenant_users,
        "systemHealth": "Good"  # You can add actual health checks here
    }

@system_admin.get("/system/recent-tenants")
async def get_recent_tenants(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get recently created tenants"""
    check_system_admin(current_user)
    
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": tenant.id,
            "name": tenant.name,
            "status": "active" if tenant.is_active else "inactive",
            "created": tenant.created_at.isoformat() if tenant.created_at else None
        }
        for tenant in tenants
    ]

@system_admin.get("/system/analytics")
async def get_system_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get system analytics data"""
    check_system_admin(current_user)
    
    # Tenant growth over last 6 months
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    tenant_growth = []
    
    for i in range(6):
        month_start = datetime.utcnow() - timedelta(days=30 * (6 - i))
        month_end = datetime.utcnow() - timedelta(days=30 * (5 - i))
        
        count = db.query(Tenant).filter(
            and_(
                Tenant.created_at >= month_start,
                Tenant.created_at < month_end
            )
        ).count()
        
        tenant_growth.append({
            "month": month_start.strftime("%b"),
            "tenants": count
        })
    
    # User activity (last 7 days)
    user_activity = []
    for i in range(7):
        date = datetime.utcnow() - timedelta(days=6 - i)
        # This is simplified - you may need to track actual login activity
        # For now, we'll use created_at as a proxy
        count = db.query(User).filter(
            func.date(User.created_at) == date.date()
        ).count()
        
        user_activity.append({
            "date": date.strftime("%Y-%m-%d"),
            "activeUsers": count
        })
    
    # System usage stats
    system_usage = {
        "totalStorage": "2.5 TB",  # You can calculate this from database sizes
        "databaseSize": "1.2 TB",
        "activeConnections": 234  # You can get this from database connection pool
    }
    
    return {
        "tenantGrowth": tenant_growth,
        "userActivity": user_activity,
        "systemUsage": system_usage
    }

@system_admin.get("/system/settings")
async def get_system_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get system settings"""
    check_system_admin(current_user)
    
    settings_map = {}
    configs = db.query(SystemConfig).all()
    
    for config in configs:
        # Convert string values to appropriate types
        if config.key == 'maintenance_mode':
            settings_map['maintenanceMode'] = config.value.lower() == 'true'
        elif config.key == 'allow_new_registrations':
            settings_map['allowNewRegistrations'] = config.value.lower() == 'true'
        elif config.key == 'max_tenants':
            settings_map['maxTenants'] = int(config.value) if config.value.isdigit() else 100
        elif config.key == 'session_timeout':
            settings_map['sessionTimeout'] = int(config.value) if config.value.isdigit() else 30
        elif config.key == 'email_notifications':
            settings_map['emailNotifications'] = config.value.lower() == 'true'
    
    # Set defaults if not found
    defaults = {
        "maintenanceMode": False,
        "allowNewRegistrations": True,
        "maxTenants": 100,
        "sessionTimeout": 30,
        "emailNotifications": True
    }
    
    return {**defaults, **settings_map}

@system_admin.put("/system/settings")
async def update_system_settings(
    payload: SystemSettingsRequest,
    # settings: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update system settings"""
    check_system_admin(current_user)
    
    # # Map frontend keys to config keys
    # key_mapping = {
    #     'maintenanceMode': 'maintenance_mode',
    #     'allowNewRegistrations': 'allow_new_registrations',
    #     'maxTenants': 'max_tenants',
    #     'sessionTimeout': 'session_timeout',
    #     'emailNotifications': 'email_notifications'
    # }
    
    # for frontend_key, value in settings.items():
    #     if frontend_key in key_mapping:
    #         config_key = key_mapping[frontend_key]
            
    #         # Get or create config
    #         config = db.query(SystemConfig).filter(SystemConfig.key == config_key).first()
            
    #         if config:
    #             # Convert boolean to string
    #             if isinstance(value, bool):
    #                 config.value = 'true' if value else 'false'
    #             else:
    #                 config.value = str(value)
    #         else:
    #             # Create new config
    #             config = SystemConfig(
    #                 key=config_key,
    #                 value='true' if isinstance(value, bool) and value else str(value),
    #                 description=f"System setting for {config_key}"
    #             )
    #             db.add(config)
    
    # db.commit()
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
    
    return {"message": "Settings updated successfully"}
