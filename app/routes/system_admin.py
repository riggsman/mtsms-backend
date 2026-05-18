from fastapi import APIRouter, Depends, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
from app.helpers.user_roles import (
    user_is_system_admin,
    user_is_system_super_admin,
    user_is_tenant_super_admin_or_system,
    user_roles_list,
    user_system_permissions_list,
)
from app.models.user import User
from app.models.tenant import Tenant
from app.models.system_config import SystemConfig
from app.models.system_settings import SystemSettings
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

from app.routes.system_settings import _get_or_create_singleton
from app.schemas.system_settings import FirebaseMessagingConfig, SystemSettingsRequest
from app.schemas.system_user_permissions import (
    SystemUserPermissionRow,
    SystemUserPermissionsListResponse,
    SystemUserPermissionsUpdate,
)

system_admin = APIRouter()

KNOWN_SYSTEM_PERMISSION_KEYS = ("database_config",)

def check_system_admin(current_user: User):
    """Helper to check if user is system admin"""
    if not user_is_tenant_super_admin_or_system(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required system admin role"
        )


def _require_system_super_admin(current_user: User) -> None:
    if not user_is_system_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system super admin can perform this action",
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

    # Suspended tenants (inactive with suspension metadata)
    suspended_tenants = db.query(Tenant).filter(
        Tenant.is_active == False,
        or_(
            Tenant.suspended_at.isnot(None),
            Tenant.suspension_reason.isnot(None),
        ),
    ).count()
    
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
        "suspendedTenants": suspended_tenants,
        "totalUsers": total_users,
        "systemUsers": system_users,
        "tenantUsers": tenant_users,
        "systemHealth": "Good"  # You can add actual health checks here
    }

@system_admin.get("/system/recent-tenants")
async def get_recent_tenants(
    limit: int = Query(10, ge=1, le=1000),
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
    
    # Tenant growth over last 12 months with trend
    tenant_growth = []
    now = datetime.utcnow()
    
    for i in range(12):
        month_start = now - timedelta(days=30 * (12 - i))
        month_end = now - timedelta(days=30 * (11 - i))
        
        count = db.query(Tenant).filter(
            and_(
                Tenant.created_at >= month_start,
                Tenant.created_at < month_end
            )
        ).count()
        
        tenant_growth.append({
            "month": month_start.strftime("%b %Y"),
            "monthShort": month_start.strftime("%b"),
            "tenants": count,
            "cumulative": count
        })
    
    # Calculate cumulative totals
    cumulative = 0
    for item in tenant_growth:
        cumulative += item["tenants"]
        item["cumulative"] = cumulative
    
    # Calculate trend
    if len(tenant_growth) >= 2:
        recent_avg = sum(item["tenants"] for item in tenant_growth[-3:]) / min(3, len(tenant_growth))
        older_avg = sum(item["tenants"] for item in tenant_growth[:-3]) / max(1, len(tenant_growth) - 3)
        tenant_growth_trend = "up" if recent_avg > older_avg else "down" if recent_avg < older_avg else "stable"
        tenant_growth_change = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
    else:
        tenant_growth_trend = "stable"
        tenant_growth_change = 0
    
    # User activity (last 30 days) with trend
    user_activity = []
    
    for i in range(30):
        date = now - timedelta(days=29 - i)
        count = db.query(User).filter(
            func.date(User.created_at) == date.date()
        ).count()
        
        user_activity.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": date.strftime("%a"),
            "activeUsers": count,
            "newUsers": count
        })
    
    # Calculate cumulative for users
    cumulative = 0
    for item in user_activity:
        cumulative += item["newUsers"]
        item["cumulative"] = cumulative
    
    # Calculate user trend
    if len(user_activity) >= 7:
        recent_week = sum(item["activeUsers"] for item in user_activity[-7:])
        prev_week = sum(item["activeUsers"] for item in user_activity[-14:-7]) if len(user_activity) >= 14 else recent_week
        user_activity_trend = "up" if recent_week > prev_week else "down" if recent_week < prev_week else "stable"
        user_activity_change = ((recent_week - prev_week) / prev_week * 100) if prev_week > 0 else 0
    else:
        user_activity_trend = "stable"
        user_activity_change = 0
    
    # Total counts
    total_tenants = db.query(Tenant).count()
    total_users = db.query(User).count()
    
    # System usage stats - dynamic for both Windows and Linux
    try:
        import platform
        import os
        import shutil
        from pathlib import Path
        
        system_info = platform.system()  # 'Windows' or 'Linux'
        base_path = Path(__file__).parent.parent
        
        # Get storage info
        try:
            usage = shutil.disk_usage(base_path.parent if base_path.name == 'app' else base_path)
            total_storage_gb = usage.total / (1024 ** 3)
            used_storage_gb = usage.used / (1024 ** 3)
            free_storage_gb = usage.free / (1024 ** 3)
            storage_percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
        except Exception:
            total_storage_gb = used_storage_gb = free_storage_gb = storage_percent = 0
        
        # Get memory info (works on both Windows and Linux)
        try:
            import psutil
            memory = psutil.virtual_memory()
            total_memory_gb = memory.total / (1024 ** 3)
            available_memory_gb = memory.available / (1024 ** 3)
            memory_percent = memory.percent
        except ImportError:
            total_memory_gb = available_memory_gb = memory_percent = 0
        
        # Get database connection info
        try:
            from app.database.base import engine
            active_connections = engine.pool.size()
            checked_out = engine.pool.checkedout()
        except Exception:
            active_connections = checked_out = 0
        
        system_usage = {
            "platform": system_info,
            "pythonVersion": platform.python_version(),
            "totalStorageGB": round(total_storage_gb, 2),
            "usedStorageGB": round(used_storage_gb, 2),
            "freeStorageGB": round(free_storage_gb, 2),
            "storagePercent": round(storage_percent, 2),
            "totalMemoryGB": round(total_memory_gb, 2) if total_memory_gb > 0 else "N/A",
            "availableMemoryGB": round(available_memory_gb, 2) if available_memory_gb > 0 else "N/A",
            "memoryPercent": round(memory_percent, 2) if memory_percent > 0 else "N/A",
            "activeConnections": active_connections,
            "checkedOutConnections": checked_out,
            "processorCount": platform.python_version() and os.cpu_count() or "N/A",
            "machine": platform.machine(),
            "processor": platform.processor() or platform.system(),
        }
    except Exception as e:
        system_usage = {
            "error": str(e),
            "platform": "unknown"
        }
    
    return {
        "tenantGrowth": tenant_growth,
        "tenantGrowthTrend": tenant_growth_trend,
        "tenantGrowthChange": round(tenant_growth_change, 1),
        "totalTenants": total_tenants,
        "userActivity": user_activity,
        "userActivityTrend": user_activity_trend,
        "userActivityChange": round(user_activity_change, 1),
        "totalUsers": total_users,
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
        "emailNotifications": True,
        "firebaseMessaging": None
    }
    
    # Fetch firebase config from system_settings table
    from app.models.system_settings import SystemSettings as GlobalSystemSettings
    sys_settings = db.query(GlobalSystemSettings).order_by(GlobalSystemSettings.id.asc()).first()
    if sys_settings and (sys_settings.firebase_messaging_enabled or sys_settings.firebase_api_key):
        defaults["firebaseMessaging"] = {
            "enabled": sys_settings.firebase_messaging_enabled or False,
            "apiKey": sys_settings.firebase_api_key,
            "authDomain": sys_settings.firebase_auth_domain,
            "projectId": sys_settings.firebase_project_id,
            "storageBucket": sys_settings.firebase_storage_bucket,
            "messagingSenderId": sys_settings.firebase_messaging_sender_id,
            "appId": sys_settings.firebase_app_id,
            "vapidKey": sys_settings.firebase_vapid_key,
            "measurementId": sys_settings.firebase_measurement_id,
            "serviceAccountUploaded": sys_settings.firebase_service_account_uploaded or False,
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
    if not user_is_system_admin(current_user):
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
        if fm.storageBucket is not None:
            settings.firebase_storage_bucket = fm.storageBucket
        if fm.measurementId is not None:
            settings.firebase_measurement_id = fm.measurementId

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
            storageBucket=settings.firebase_storage_bucket,
            measurementId=settings.firebase_measurement_id,
            serviceAccountUploaded=settings.firebase_service_account_uploaded,
        )
    
    return {"message": "Settings updated successfully"}


@system_admin.post("/system/firebase-service-account")
async def upload_firebase_service_account(
    file_data: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Upload Firebase service account JSON file for FCM Admin SDK.
    File is saved to app/firebase/serviceAccount.json
    """
    check_system_admin(current_user)
    
    from pathlib import Path
    
    firebase_dir = Path(__file__).parent.parent / "firebase"
    firebase_dir.mkdir(exist_ok=True)
    file_path = firebase_dir / "serviceAccount.json"
    
    try:
        content = await file_data.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
        if settings:
            settings.firebase_service_account_uploaded = True
            db.commit()
        
        return {"message": "Service account uploaded", "path": str(file_path)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


@system_admin.get(
    "/system/system-users/permissions",
    response_model=SystemUserPermissionsListResponse,
)
async def list_system_users_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """List SYSTEM users and their extra capability keys (system super admin only)."""
    _require_system_super_admin(current_user)
    rows = (
        db.query(User)
        .filter(
            User.user_type == "SYSTEM",
            User.deleted_at.is_(None),
        )
        .order_by(User.id.asc())
        .all()
    )
    items: List[SystemUserPermissionRow] = []
    for u in rows:
        items.append(
            SystemUserPermissionRow(
                id=u.id,
                username=u.username,
                email=u.email,
                firstname=u.firstname,
                lastname=u.lastname,
                roles=user_roles_list(u),
                system_permissions=user_system_permissions_list(u),
            )
        )
    return SystemUserPermissionsListResponse(
        items=items,
        known_permissions=list(KNOWN_SYSTEM_PERMISSION_KEYS),
    )


@system_admin.put(
    "/system/system-users/{user_id}/permissions",
    response_model=SystemUserPermissionRow,
)
async def update_system_user_permissions(
    user_id: int,
    body: SystemUserPermissionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Grant or revoke extra capabilities for a SYSTEM user (system super admin only)."""
    _require_system_super_admin(current_user)
    target = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.user_type == "SYSTEM",
            User.deleted_at.is_(None),
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System user not found")

    allowed = set(KNOWN_SYSTEM_PERMISSION_KEYS)
    cleaned = [p for p in (body.system_permissions or []) if p in allowed]
    target.system_permissions = cleaned or None
    db.commit()
    db.refresh(target)

    return SystemUserPermissionRow(
        id=target.id,
        username=target.username,
        email=target.email,
        firstname=target.firstname,
        lastname=target.lastname,
        roles=user_roles_list(target),
        system_permissions=user_system_permissions_list(target),
    )


from app.routes import platform_analytics

system_admin.include_router(platform_analytics.router)
