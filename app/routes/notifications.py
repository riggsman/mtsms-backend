"""
FCM web push: register tokens (tenant-scoped) using JWT auth.
Global system_settings.firebase_messaging_enabled must be true.
"""
import datetime
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, func, cast, String
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.dependencies.auth import get_current_user_tenant, get_current_user, require_any_role
from app.dependencies.tenantDependency import get_db
from app.models.role import UserRole
from app.models.user import User
from app.models.user_push_token import UserPushToken
from app.models.tenant import Tenant
from app.models.push_notification_log import PushNotificationLog
from app.schemas.notifications import FcmTokenRegisterRequest, FcmTestPushResponse
from app.services.fcm_service import is_fcm_messaging_enabled_globally, send_fcm_test_push_to_users, send_fcm_notification_to_users
from app.helpers.user_roles import user_is_system_admin

notifications_router = APIRouter()


class PushNotificationRequest(BaseModel):
    title: str
    body: str
    target_tenants: Optional[List[int]] = None
    target_roles: Optional[List[str]] = None


class PushNotificationResponse(BaseModel):
    success: bool
    message: str
    recipients_count: int = 0
    log_id: int = 0


class PushLogsResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int


def _push_logs_filter_for_institution(db: Session, institution_id: int):
    """Broadcast (no tenant filter) or JSON array contains this institution id."""
    col = PushNotificationLog.target_tenants
    dialect = db.get_bind().dialect.name
    if dialect in ("mysql", "mariadb"):
        return or_(
            col.is_(None),
            func.json_contains(col, json.dumps(institution_id), "$"),
        )
    # SQLite / others: match quoted id in JSON text
    as_text = cast(col, String)
    return or_(
        col.is_(None),
        as_text.contains(json.dumps(institution_id)),
        as_text.contains(f'"{institution_id}"'),
    )


@notifications_router.get("/notifications/tenant/push-logs", response_model=PushLogsResponse)
def get_tenant_push_notification_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    """
    Push notification history visible to this tenant (admin / secretary).
    Includes all-tenant broadcasts and sends explicitly targeted at this institution.
    """
    inst_id = current_user.institution_id
    if not inst_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institution context is required.",
        )

    filt = _push_logs_filter_for_institution(db, inst_id)
    q = db.query(PushNotificationLog).filter(filt)
    total = q.count()
    offset = (page - 1) * page_size
    logs = (
        q.order_by(PushNotificationLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": log.id,
                "title": log.title,
                "body": log.body,
                "target_tenants": log.target_tenants,
                "target_roles": log.target_roles,
                "status": log.status,
                "success_count": log.success_count,
                "failure_count": log.failure_count,
                "failure_reason": log.failure_reason,
                "sent_by_user_id": log.sent_by_user_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@notifications_router.get("/notifications/push-logs", response_model=PushLogsResponse)
def get_push_notification_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get push notification history (system admin only)."""
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin can view push notification logs",
        )
    
    offset = (page - 1) * page_size
    logs = db.query(PushNotificationLog).order_by(
        PushNotificationLog.created_at.desc()
    ).offset(offset).limit(page_size).all()
    
    total = db.query(PushNotificationLog).count()
    
    return {
        "items": [
            {
                "id": log.id,
                "title": log.title,
                "body": log.body,
                "target_tenants": log.target_tenants,
                "target_roles": log.target_roles,
                "status": log.status,
                "success_count": log.success_count,
                "failure_count": log.failure_count,
                "failure_reason": log.failure_reason,
                "sent_by_user_id": log.sent_by_user_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@notifications_router.post(
    "/notifications/test-push",
    response_model=FcmTestPushResponse,
)
def send_test_push_to_current_user(
    db: Session = Depends(get_db),
    global_db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_tenant),
):
    """
    Sends a real FCM notification to **this user's** registered device tokens only.
    Use to verify browser push: allow notifications, then click once (foreground tab shows a notification too).
    """
    if not is_fcm_messaging_enabled_globally(global_db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase Cloud Messaging is disabled in system settings.",
        )
    payload = send_fcm_test_push_to_users(
        db,
        global_db,
        [current_user.id],
        title="MTSMS — Web push test",
        body="If you see this on your PC, FCM is working.",
    )
    return FcmTestPushResponse.model_validate(payload)


@notifications_router.post("/notifications/fcm-token", status_code=status.HTTP_204_NO_CONTENT)
def register_fcm_token(
    body: FcmTokenRegisterRequest,
    db: Session = Depends(get_db),
    global_db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_tenant),
):
    if not is_fcm_messaging_enabled_globally(global_db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase Cloud Messaging is disabled in system settings.",
        )
    now = datetime.datetime.utcnow()
    existing = (
        db.query(UserPushToken)
        .filter(
            UserPushToken.user_id == current_user.id,
            UserPushToken.token == body.token,
        )
        .first()
    )
    if existing:
        existing.last_seen_at = now
        if body.user_agent is not None:
            existing.user_agent = body.user_agent[:500]
    else:
        db.add(
            UserPushToken(
                user_id=current_user.id,
                institution_id=current_user.institution_id,
                token=body.token,
                user_agent=(body.user_agent or "")[:500] if body.user_agent else None,
                created_at=now,
                last_seen_at=now,
            )
        )
    db.commit()
    return None


@notifications_router.delete("/notifications/fcm-token", status_code=status.HTTP_204_NO_CONTENT)
def unregister_fcm_token(
    token: Optional[str] = Query(None, description="If omitted, all FCM tokens for this user are removed."),
    db: Session = Depends(get_db),
    global_db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_tenant),
):
    if not is_fcm_messaging_enabled_globally(global_db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase Cloud Messaging is disabled in system settings.",
        )
    q = db.query(UserPushToken).filter(UserPushToken.user_id == current_user.id)
    if token:
        q = q.filter(UserPushToken.token == token)
    q.delete(synchronize_session=False)
    db.commit()
    return None


@notifications_router.post(
    "/notifications/push",
    response_model=PushNotificationResponse,
)
def send_push_notification(
    body: PushNotificationRequest,
    db: Session = Depends(get_db),
    global_db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Send push notification to users.
    System admin can send to all tenants or specific tenants.
    Can filter by roles (student, teacher, etc.).
    """
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin can send push notifications",
        )
    
    if not is_fcm_messaging_enabled_globally(global_db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase Cloud Messaging is disabled in system settings.",
        )
    
    # Create log entry
    log_entry = PushNotificationLog(
        title=body.title,
        body=body.body,
        target_tenants=body.target_tenants,
        target_roles=body.target_roles,
        status="pending",
        sent_by_user_id=current_user.id,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    target_user_ids = []
    
    if body.target_tenants and len(body.target_tenants) > 0:
        tenants = db.query(Tenant).filter(Tenant.id.in_(body.target_tenants)).all()
        for tenant in tenants:
            push_tokens = db.query(UserPushToken).filter(
                UserPushToken.institution_id == tenant.id
            ).all()
            target_user_ids.extend([t.user_id for t in push_tokens])
    else:
        push_tokens = db.query(UserPushToken).all()
        target_user_ids = [t.user_id for t in push_tokens]
    
    if body.target_roles and len(body.target_roles) > 0:
        users = db.query(User).filter(
            User.id.in_(target_user_ids),
            User.role.in_(body.target_roles)
        ).all()
        target_user_ids = [u.id for u in users]
    
    target_user_ids = list(set(target_user_ids))
    
    if not target_user_ids:
        log_entry.mark_as_sent(success=0, failure=0)
        db.commit()
        return PushNotificationResponse(
            success=True,
            message="No users found with push tokens",
            recipients_count=0
        )
    
    # Send the notification
    result = send_fcm_notification_to_users(
        db,
        global_db,
        target_user_ids,
        title=body.title,
        body=body.body,
    )
    
    # Update log with results
    log_entry.send_metadata = {
        "tokens_targeted": result.get("tokens_targeted", 0),
        "ok": result.get("ok", False),
    }
    
    if result.get("ok", False):
        log_entry.mark_as_sent(
            success=result.get("success", 0),
            failure=result.get("failure", 0),
        )
    else:
        log_entry.mark_as_failed({
            "reason": result.get("reason"),
            "detail": result.get("detail"),
        })
    
    db.commit()
    
    return PushNotificationResponse(
        success=result.get("ok", False),
        message=f"Push notification sent - {result.get('success', 0)} delivered, {result.get('failure', 0)} failed",
        recipients_count=result.get("success", 0),
        log_id=log_entry.id
    )
