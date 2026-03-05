"""
Payment API - CRUD operations for payments
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import secrets
import string

from app.models.payment import Payment
from app.models.student import Student
from app.models.user import User
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PaymentResponse
)
from app.exceptions import NotFoundError, ValidationError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity
from app.services.email_service import EmailService
from app.services.email_tracker import EmailTracker
from app.helpers.async_helper import run_async_safe
from app.conf.config import settings
import logging

logger = logging.getLogger(__name__)
from app.conf.config import settings
import logging

logger = logging.getLogger(__name__)
from app.services.email_tracker import EmailTracker
from app.helpers.async_helper import run_async_safe


def generate_transaction_id() -> str:
    """Generate a unique transaction ID"""
    return f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"


def generate_receipt_number(institution_id: int) -> str:
    """Generate a unique receipt number"""
    timestamp = datetime.utcnow().strftime('%Y%m%d')
    random_part = ''.join(secrets.choice(string.digits) for _ in range(6))
    return f"RCP-{institution_id}-{timestamp}-{random_part}"


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def initiate_payment(
    db: Session,
    payment_request: PaymentInitiateRequest,
    current_user: Optional[User] = None,
    institution_id: Optional[int] = None
) -> PaymentInitiateResponse:
    """Initiate a payment and send OTP to student email"""
    # Get institution_id
    final_institution_id = institution_id
    if not final_institution_id and current_user:
        final_institution_id = current_user.institution_id
    
    if not final_institution_id:
        raise ValidationError("institution_id is required to create a payment")
    
    # Get student information
    student = db.query(Student).filter(
        Student.id == payment_request.student_id,
        Student.institution_id == final_institution_id,
        Student.deleted_at.is_(None)
    ).first()
    
    if not student:
        raise NotFoundError(f"Student with ID {payment_request.student_id} not found")
    
    # Verify student email matches
    if student.email != payment_request.student_email:
        raise ValidationError("Student email does not match")
    
    # Generate transaction ID and OTP
    transaction_id = generate_transaction_id()
    otp = generate_otp()
    
    # Create payment record
    payment = Payment(
        institution_id=final_institution_id,
        student_id=payment_request.student_id,
        student_id_number=student.student_id,
        student_name=f"{student.firstname} {student.lastname}".strip(),
        student_email=payment_request.student_email,
        amount=payment_request.amount,
        currency='XAF',
        provider=payment_request.provider.upper(),
        reason=payment_request.reason,
        phone_number=payment_request.phone_number,
        transaction_id=transaction_id,
        status='pending',
        payment_method=f"{payment_request.provider.upper()} Mobile Money",
        otp_sent=otp,
        otp_sent_at=datetime.utcnow()
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Send OTP email to student asynchronously
    try:
        email_subject = "Payment Verification OTP"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Payment Verification OTP</h2>
                <p>Dear {student.firstname} {student.lastname},</p>
                <p>You have initiated a payment of <strong>{payment_request.amount} XAF</strong> for: <strong>{payment_request.reason}</strong></p>
                <p>Please use the following OTP to complete your payment:</p>
                <div style="background-color: #f8f9fa; border: 2px solid #3498db; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #3498db; margin: 0; font-size: 32px; letter-spacing: 5px;">{otp}</h1>
                </div>
                <p><strong>This OTP is valid for 10 minutes.</strong></p>
                <p style="color: #dc3545;">If you did not initiate this payment, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                <p style="color: #6c757d; font-size: 12px;">Best regards,<br>School Management System</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Dear {student.firstname} {student.lastname},

You have initiated a payment of {payment_request.amount} XAF for: {payment_request.reason}

Please use the following OTP to complete your payment:

OTP: {otp}

This OTP is valid for 10 minutes.

If you did not initiate this payment, please ignore this email.

Best regards,
School Management System
        """
        
        # Send email with tracking asynchronously
        async def send_otp_email():
            try:
                await EmailTracker.send_with_tracking(
                    db=db,
                    sender_email=settings.SMTP_FROM_EMAIL,
                    recipient_email=payment_request.student_email,
                    subject=email_subject,
                    html_content=html_content,
                    text_content=text_content,
                    institution_id=final_institution_id
                )
            except Exception as e:
                logger.error(f"Error sending OTP email: {e}")
        
        run_async_safe(send_otp_email())
    except Exception as e:
        logger.error(f"Error setting up OTP email: {e}")
        # Don't fail the payment initiation if email fails
    
    # Log activity
    if current_user:
        try:
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="payment",
                entity_id=payment.id,
                entity_name=f"Payment {transaction_id}",
                institution_id=final_institution_id,
                content=f"Initiated payment: {payment_request.amount} XAF for {payment_request.reason}"
            )
        except Exception as e:
            print(f"Error logging payment activity: {e}")
    
    return PaymentInitiateResponse(
        transaction_id=transaction_id,
        message="Payment initiated. OTP sent to your email.",
        otp_sent=True
    )


def verify_payment(
    db: Session,
    verify_request: PaymentVerifyRequest,
    current_user: Optional[User] = None,
    institution_id: Optional[int] = None
) -> PaymentVerifyResponse:
    """Verify payment with OTP and complete the transaction"""
    # Get payment by transaction_id
    payment = db.query(Payment).filter(
        Payment.transaction_id == verify_request.transaction_id,
        Payment.deleted_at.is_(None)
    ).first()
    
    if not payment:
        raise NotFoundError(f"Payment with transaction ID {verify_request.transaction_id} not found")
    
    # Check if payment is already completed
    if payment.status == 'paid':
        raise ValidationError("Payment has already been completed")
    
    # Verify OTP
    if payment.otp_sent != verify_request.otp:
        raise ValidationError("Invalid OTP")
    
    # Check if OTP is expired (10 minutes)
    if payment.otp_sent_at:
        time_diff = datetime.utcnow() - payment.otp_sent_at
        if time_diff.total_seconds() > 600:  # 10 minutes
            payment.status = 'failed'
            db.commit()
            raise ValidationError("OTP has expired. Please initiate a new payment.")
    
    # Generate receipt number
    receipt_number = generate_receipt_number(payment.institution_id)
    
    # Update payment status
    payment.status = 'paid'
    payment.receipt_number = receipt_number
    payment.otp_verified = True
    payment.otp_verified_at = datetime.utcnow()
    payment.paid_at = datetime.utcnow()
    
    db.commit()
    db.refresh(payment)
    
    # Log activity
    if current_user:
        try:
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="payment",
                entity_id=payment.id,
                entity_name=f"Payment {payment.transaction_id}",
                institution_id=payment.institution_id,
                content=f"Payment verified and completed: {payment.amount} XAF - Receipt: {receipt_number}"
            )
        except Exception as e:
            print(f"Error logging payment activity: {e}")
    
    # Convert payment to response
    payment_response = PaymentResponse.from_payment(payment)
    
    return PaymentVerifyResponse(
        success=True,
        transaction_id=payment.transaction_id,
        receipt_number=receipt_number,
        message="Payment verified and completed successfully",
        payment=payment_response
    )


def get_payment(
    db: Session,
    payment_id: int,
    institution_id: Optional[int] = None
) -> Payment:
    """Get a payment by ID"""
    query = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.deleted_at.is_(None)
    )
    
    if institution_id is not None:
        query = query.filter(Payment.institution_id == institution_id)
    
    payment = query.first()
    if not payment:
        raise NotFoundError(f"Payment with ID {payment_id} not found")
    
    return payment


def get_payment_by_receipt(
    db: Session,
    receipt_number: str,
    institution_id: Optional[int] = None
) -> Payment:
    """Get a payment by receipt number"""
    query = db.query(Payment).filter(
        Payment.receipt_number == receipt_number,
        Payment.deleted_at.is_(None)
    )
    
    if institution_id is not None:
        query = query.filter(Payment.institution_id == institution_id)
    
    payment = query.first()
    if not payment:
        raise NotFoundError(f"Payment with receipt number {receipt_number} not found")
    
    return payment


def get_payments(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    institution_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[List[Payment], int]:
    """Get list of payments with pagination and filters"""
    query = db.query(Payment).filter(Payment.deleted_at.is_(None))
    
    if institution_id is not None:
        query = query.filter(Payment.institution_id == institution_id)
    
    if student_id is not None:
        query = query.filter(Payment.student_id == student_id)
    
    if status:
        query = query.filter(Payment.status == status.lower())
    
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    
    # Order by created_at descending (newest first)
    query = query.order_by(Payment.created_at.desc())
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def get_student_payments(
    db: Session,
    student_id: int,
    skip: int = 0,
    limit: int = 100,
    institution_id: Optional[int] = None
) -> Tuple[List[Payment], int]:
    """Get payments for a specific student"""
    return get_payments(
        db=db,
        skip=skip,
        limit=limit,
        institution_id=institution_id,
        student_id=student_id
    )


def update_payment(
    db: Session,
    payment_id: int,
    status: Optional[str] = None,
    description: Optional[str] = None,
    current_user: Optional[User] = None,
    institution_id: Optional[int] = None
) -> Payment:
    """Update a payment (typically for admin updates)"""
    payment = get_payment(db, payment_id, institution_id=institution_id)
    
    if status:
        valid_statuses = ['pending', 'paid', 'failed', 'cancelled']
        if status.lower() not in valid_statuses:
            raise ValidationError(f"Status must be one of: {', '.join(valid_statuses)}")
        payment.status = status.lower()
        
        if status.lower() == 'paid' and not payment.paid_at:
            payment.paid_at = datetime.utcnow()
    
    if description:
        payment.description = description
    
    payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)
    
    # Log activity
    if current_user:
        try:
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="payment",
                entity_id=payment.id,
                entity_name=f"Payment {payment.transaction_id}",
                institution_id=payment.institution_id,
                content=f"Updated payment: {payment.transaction_id}"
            )
        except Exception as e:
            print(f"Error logging payment activity: {e}")
    
    return payment


def delete_payment(
    db: Session,
    payment_id: int,
    current_user: Optional[User] = None,
    institution_id: Optional[int] = None
) -> bool:
    """Soft delete a payment"""
    payment = get_payment(db, payment_id, institution_id=institution_id)
    payment.deleted_at = datetime.utcnow()
    db.commit()
    return True
