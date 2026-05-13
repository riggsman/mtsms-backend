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
from app.models.department import Department
from app.models.specialty import Specialization
from app.models.tenant import Tenant
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PaymentResponse,
    PaymentPublicVerificationResponse,
)
from app.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity
from app.services.email_tracker import EmailTracker
from app.helpers.async_helper import run_async_safe
from app.database.sessionManager import create_standalone_db_session
from app.conf.config import settings
import logging

logger = logging.getLogger(__name__)


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


def _dept_and_spec_names_for_student(
    db: Session, student: Optional[Student]
) -> Tuple[Optional[str], Optional[str]]:
    if not student:
        return None, None
    dept_name = None
    spec_name = None
    if student.department_id:
        d = (
            db.query(Department)
            .filter(
                Department.id == student.department_id,
                Department.deleted_at.is_(None),
            )
            .first()
        )
        if d:
            dept_name = d.name
    if student.specialization_id:
        sp = (
            db.query(Specialization)
            .filter(
                Specialization.id == student.specialization_id,
                Specialization.deleted_at.is_(None),
            )
            .first()
        )
        if sp:
            spec_name = sp.name
    return dept_name, spec_name


def payment_to_response(db: Session, payment: Payment) -> PaymentResponse:
    """PaymentResponse with department/specialization for receipts and lists."""
    student = (
        db.query(Student)
        .filter(Student.id == payment.student_id, Student.deleted_at.is_(None))
        .first()
    )
    dept, spec = _dept_and_spec_names_for_student(db, student)
    return PaymentResponse.from_payment(
        payment, department_name=dept, specialization_name=spec
    )


def payments_to_responses(db: Session, payments: List[Payment]) -> List[PaymentResponse]:
    """Batch version: avoids N+1 department/specialization lookups."""
    if not payments:
        return []
    student_ids = {p.student_id for p in payments}
    students = (
        db.query(Student)
        .filter(Student.id.in_(student_ids), Student.deleted_at.is_(None))
        .all()
    )
    by_sid = {s.id: s for s in students}
    dept_ids = {s.department_id for s in students if s.department_id}
    spec_ids = {s.specialization_id for s in students if s.specialization_id}
    dept_by_id: dict = {}
    if dept_ids:
        for d in (
            db.query(Department)
            .filter(Department.id.in_(dept_ids), Department.deleted_at.is_(None))
            .all()
        ):
            dept_by_id[d.id] = d.name
    spec_by_id: dict = {}
    if spec_ids:
        for sp in (
            db.query(Specialization)
            .filter(Specialization.id.in_(spec_ids), Specialization.deleted_at.is_(None))
            .all()
        ):
            spec_by_id[sp.id] = sp.name
    out: List[PaymentResponse] = []
    for p in payments:
        st = by_sid.get(p.student_id)
        dn = dept_by_id.get(st.department_id) if st and st.department_id else None
        sn = spec_by_id.get(st.specialization_id) if st and st.specialization_id else None
        out.append(
            PaymentResponse.from_payment(
                p, department_name=dn, specialization_name=sn
            )
        )
    return out


def get_public_payment_verification(
    db: Session, transaction_id: str, institution_id: int
) -> PaymentPublicVerificationResponse:
    """
    Lookup payment by transaction_id and institution_id (public receipt verification).
    Uses the default app database session (same as tenant catalog / shared tenant DB).
    """
    payment = (
        db.query(Payment)
        .filter(
            Payment.transaction_id == transaction_id,
            Payment.institution_id == institution_id,
            Payment.deleted_at.is_(None),
        )
        .first()
    )
    if not payment:
        raise NotFoundError("No payment found for this verification link")
    pr = payment_to_response(db, payment)
    inst_name = None
    try:
        t = db.query(Tenant).filter(Tenant.id == institution_id).first()
        if t:
            inst_name = t.name
    except Exception:
        pass
    return PaymentPublicVerificationResponse(payment=pr, institution_name=inst_name)


def initiate_payment(
    db: Session,
    payment_request: PaymentInitiateRequest,
    current_user: Optional[User] = None,
    institution_id: Optional[int] = None,
    tenant_name: Optional[str] = None,
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
    
    # Verify student email matches request (case-insensitive)
    req_em = str(payment_request.student_email or "").strip().lower()
    st_em = (student.email or "").strip().lower()
    if req_em != st_em:
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

    # Log on the request session before any background work (avoids racing another thread on db)
    if current_user:
        try:
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="payment",
                entity_id=payment.id,
                entity_name=f"Payment {transaction_id}",
                institution_id=final_institution_id,
                content=f"Initiated payment: {payment_request.amount} XAF for {payment_request.reason}",
            )
        except Exception as e:
            logger.warning("Error logging payment activity: %s", e)

    # Send OTP email asynchronously using its own DB session (request session is not thread-safe)
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
        
        async def send_otp_email():
            db_email = create_standalone_db_session(tenant_name)
            try:
                await EmailTracker.send_with_tracking(
                    db=db_email,
                    sender_email=settings.SMTP_FROM_EMAIL,
                    recipient_email=payment_request.student_email,
                    subject=email_subject,
                    html_content=html_content,
                    text_content=text_content,
                    institution_id=final_institution_id,
                )
            except Exception as e:
                logger.error("Error sending OTP email: %s", e)
            finally:
                db_email.close()

        run_async_safe(send_otp_email())
    except Exception as e:
        logger.error("Error setting up OTP email: %s", e)

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

    try:
        from app.apis.student_payment import apply_completed_online_payment

        apply_completed_online_payment(db, payment)
    except Exception as e:
        logger.warning("Could not allocate payment to fee installments: %s", e)
    
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
    
    payment_response = payment_to_response(db, payment)

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


def cancel_student_pending_payment(
    db: Session,
    payment_id: int,
    current_user: User,
    institution_id: Optional[int] = None,
) -> None:
    """Student abandons an incomplete online payment (pending only)."""
    from app.apis.students import resolve_student_for_logged_in_user

    me = resolve_student_for_logged_in_user(db, current_user)
    if not me:
        raise NotFoundError("Student record not found for current user")

    payment = get_payment(db, payment_id, institution_id=institution_id)
    if payment.student_id != me.id:
        raise ForbiddenError("You can only remove your own payment records")

    status = (payment.status or "").lower()
    if status != "pending":
        raise ValidationError("Only pending payments can be removed. Completed payments stay on file.")

    payment.deleted_at = datetime.utcnow()
    payment.updated_at = datetime.utcnow()
    db.commit()
