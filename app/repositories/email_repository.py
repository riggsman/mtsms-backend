from sqlalchemy.orm import Session
from app.models.email_log import EmailLog
from typing import Optional
from datetime import datetime

class EmailRepository:
    """Repository for email log database operations"""
    
    @staticmethod
    def create_log(
        db: Session,
        sender_email: str,
        recipient_email: str,
        subject: str,
        institution_id: Optional[int] = None
    ) -> int:
        """Create a new email log entry"""
        email_log = EmailLog(
            sender_email=sender_email,
            recipient_email=recipient_email,
            subject=subject,
            status="PENDING",
            retry_count=0,
            institution_id=institution_id
        )
        db.add(email_log)
        db.commit()
        db.refresh(email_log)
        return email_log.id
    
    @staticmethod
    def update_after_send(
        db: Session,
        log_id: int,
        status: str,
        failure_reason: Optional[str] = None,
        provider_message_id: Optional[str] = None,
        retry_count: int = 0
    ) -> EmailLog:
        """Update email log after sending attempt"""
        email_log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
        if email_log:
            email_log.status = status
            email_log.failure_reason = failure_reason
            email_log.provider_message_id = provider_message_id
            email_log.retry_count = retry_count
            email_log.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(email_log)
        return email_log
    
    @staticmethod
    def update_delivery_status(
        db: Session,
        provider_message_id: str,
        new_status: str
    ) -> Optional[EmailLog]:
        """Update email log delivery status via webhook"""
        email_log = db.query(EmailLog).filter(
            EmailLog.provider_message_id == provider_message_id
        ).first()
        if email_log:
            email_log.status = new_status
            email_log.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(email_log)
        return email_log
    
    @staticmethod
    def get_logs(
        db: Session,
        institution_id: Optional[int] = None,
        status: Optional[str] = None,
        recipient_email: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[EmailLog], int]:
        """Get email logs with filtering"""
        query = db.query(EmailLog)
        
        if institution_id is not None:
            query = query.filter(EmailLog.institution_id == institution_id)
        
        if status:
            query = query.filter(EmailLog.status == status)
        
        if recipient_email:
            query = query.filter(EmailLog.recipient_email == recipient_email)
        
        total = query.count()
        logs = query.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return logs, total
    
    @staticmethod
    def get_log_by_id(db: Session, log_id: int) -> Optional[EmailLog]:
        """Get email log by ID"""
        return db.query(EmailLog).filter(EmailLog.id == log_id).first()
