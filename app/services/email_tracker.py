from sqlalchemy.orm import Session
from app.repositories.email_repository import EmailRepository
from app.services.email_service import EmailService
from app.conf.config import settings
import logging
from typing import Optional, Dict, Any
import uuid

logger = logging.getLogger(__name__)

class EmailTracker:
    """Email tracking service with retry logic"""
    
    MAX_RETRY = 3
    
    @staticmethod
    async def send_with_tracking(
        db: Session,
        sender_email: str,
        recipient_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        institution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send email with tracking and retry logic
        
        Returns:
            dict with success, status, recipient, retry_count, failure_reason, timestamp
        """
        # Create log entry
        log_id = EmailRepository.create_log(
            db=db,
            sender_email=sender_email,
            recipient_email=recipient_email,
            subject=subject,
            institution_id=institution_id
        )
        
        retry_count = 0
        status = "FAILED"
        failure_reason = None
        provider_message_id = None
        
        # Retry logic
        while retry_count < EmailTracker.MAX_RETRY:
            try:
                # Send email
                success = await EmailService.send_email(
                    to_email=recipient_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    from_email=sender_email
                )
                
                if success:
                    # Generate a provider message ID (since SMTP doesn't return one)
                    # In production, use actual provider message ID from SendGrid/Mailgun/etc.
                    provider_message_id = f"msg_{uuid.uuid4().hex[:16]}"
                    status = "SENT"
                    failure_reason = None
                    break
                else:
                    retry_count += 1
                    failure_reason = "Email service returned False"
                    if retry_count < EmailTracker.MAX_RETRY:
                        logger.warning(f"Email send failed, retrying ({retry_count}/{EmailTracker.MAX_RETRY})")
                    
            except Exception as error:
                retry_count += 1
                failure_reason = str(error)
                logger.error(f"Error sending email (attempt {retry_count}/{EmailTracker.MAX_RETRY}): {error}")
                
                if retry_count >= EmailTracker.MAX_RETRY:
                    logger.error(f"Max retries reached for email to {recipient_email}")
        
        # Update log with final status
        EmailRepository.update_after_send(
            db=db,
            log_id=log_id,
            status=status,
            failure_reason=failure_reason,
            provider_message_id=provider_message_id,
            retry_count=retry_count
        )
        
        return {
            "success": status == "SENT",
            "status": status,
            "recipient": recipient_email,
            "retry_count": retry_count,
            "failure_reason": failure_reason,
            "log_id": log_id,
            "provider_message_id": provider_message_id
        }
