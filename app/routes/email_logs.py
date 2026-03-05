from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database.base import get_db_session as get_db
from app.dependencies.auth import get_current_user, require_role, UserRole
from app.repositories.email_repository import EmailRepository
from app.models.user import User
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/email-logs", tags=["Email Logs"])


class EmailLogResponse(BaseModel):
    id: int
    sender_email: str
    recipient_email: str
    subject: Optional[str]
    status: str
    failure_reason: Optional[str]
    provider_message_id: Optional[str]
    retry_count: int
    institution_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    items: list[EmailLogResponse]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=EmailLogListResponse)
async def get_email_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    recipient_email: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get email logs with filtering
    - System admins can see all logs
    - Tenant admins can only see logs for their institution
    """
    # Determine institution_id filter
    institution_id = None
    if current_user.user_type == "TENANT":
        institution_id = current_user.institution_id
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get logs
    logs, total = EmailRepository.get_logs(
        db=db,
        institution_id=institution_id,
        status=status,
        recipient_email=recipient_email,
        skip=skip,
        limit=page_size
    )
    
    return {
        "items": logs,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats", response_model=dict)
async def get_email_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get email statistics
    - System admins see all stats
    - Tenant admins see stats for their institution only
    """
    institution_id = None
    if current_user.user_type == "TENANT":
        institution_id = current_user.institution_id
    
    # Get all logs for stats
    logs, total = EmailRepository.get_logs(
        db=db,
        institution_id=institution_id,
        skip=0,
        limit=10000  # Get all for stats
    )
    
    # Calculate statistics
    stats = {
        "total": total,
        "pending": sum(1 for log in logs if log.status == "PENDING"),
        "sent": sum(1 for log in logs if log.status == "SENT"),
        "failed": sum(1 for log in logs if log.status == "FAILED"),
        "delivered": sum(1 for log in logs if log.status == "DELIVERED"),
        "bounced": sum(1 for log in logs if log.status == "BOUNCED"),
    }
    
    return stats


@router.get("/{log_id}", response_model=EmailLogResponse)
async def get_email_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific email log by ID"""
    log = EmailRepository.get_log_by_id(db=db, log_id=log_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Email log not found")
    
    # Check permissions
    if current_user.user_type == "TENANT" and log.institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this email log")
    
    return log


@router.post("/webhook/delivery-status")
async def delivery_webhook_endpoint(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for email delivery status updates
    Called by email providers (SendGrid, Mailgun, etc.)
    """
    provider_message_id = request_data.get("message_id") or request_data.get("provider_message_id")
    event_type = request_data.get("event") or request_data.get("event_type")
    
    if not provider_message_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing message_id or event")
    
    # Map event types to statuses
    status_map = {
        "delivered": "DELIVERED",
        "bounce": "BOUNCED",
        "bounced": "BOUNCED",
        "failed": "FAILED"
    }
    
    new_status = status_map.get(event_type.lower())
    
    if not new_status:
        return {"message": "Event ignored", "event_type": event_type}
    
    # Update delivery status
    updated_log = EmailRepository.update_delivery_status(
        db=db,
        provider_message_id=provider_message_id,
        new_status=new_status
    )
    
    if not updated_log:
        return {"message": "Email log not found", "provider_message_id": provider_message_id}
    
    return {
        "message": "Status updated",
        "provider_message_id": provider_message_id,
        "new_status": new_status
    }
