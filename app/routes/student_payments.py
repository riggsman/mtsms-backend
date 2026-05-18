"""
Student Payment Routes
"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.sessionManager import get_db
from app.schemas.student_payment import (
    StudentPaymentCreate,
    StudentPaymentUpdate,
    StudentPaymentResponse,
    RecordPaymentRequest,
    StudentPaymentStatusResponse
)
from app.apis import student_payment as payment_api
from app.apis.students import resolve_student_for_logged_in_user
from app.apis.school import get_academic_year_name
from app.helpers.program_level import resolve_program_fee_level
from app.authentication.authenticator import auth_guard, AuthUser
from app.helpers.user_roles import user_has_role, user_has_any_role
from app.exceptions import ForbiddenError, NotFoundError


router = APIRouter()


def _resolve_student_id(db: Session, current_user: AuthUser) -> int:
    """Map logged-in user to students.id (not users.id)."""
    student = resolve_student_for_logged_in_user(db, current_user.user)
    if not student:
        raise NotFoundError("Student record not found for current user")
    return student.id


def _is_student_only(current_user: AuthUser) -> bool:
    """True when the user has student role but no elevated tenant admin roles."""
    if not user_has_role(current_user.user, "student"):
        return False
    return not user_has_any_role(
        current_user.user,
        ["admin", "super_admin", "secretary", "system_admin", "system_super_admin"],
    )


@router.get("/student-payments", response_model=List[StudentPaymentResponse])
def get_student_payments(
    student_id: Optional[int] = None,
    school_id: Optional[int] = None,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """
    Get all student payments for the institution.
    Admin can see all, students see only their own.
    """
    institution_id = int(currentUser.institution_id)
    
    # If student user, only show their own payments
    if user_has_role(currentUser.user, "student"):
        student_id = _resolve_student_id(db, currentUser)
    
    payments = payment_api.get_student_payments(db, institution_id, student_id, school_id)
    return [StudentPaymentResponse.from_model(p) for p in payments]


@router.get("/student-payments/fee-preview")
def get_payment_fee_preview(
    school_id: int,
    level: str,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """
    Get a preview of the total fee for a school and level combination.
    Used to show the fee before creating a payment record.
    """
    import logging
    from app.apis.fee_structure import get_installments, get_installments_for_level
    from app.helpers.program_level import normalize_program_fee_level

    logger = logging.getLogger(__name__)
    institution_id = int(currentUser.institution_id)
    level_norm = normalize_program_fee_level(level) or level.upper()

    logger.info(
        f"[fee-preview] institution_id={institution_id}, school_id={school_id}, level={level_norm}"
    )

    installments = get_installments_for_level(db, institution_id, school_id, level_norm)
    logger.info(f"[fee-preview] Found {len(installments)} installments for level={level_norm}")

    all_installments = get_installments(db, institution_id, school_id)
    available_levels = sorted({inst.level.upper() for inst in all_installments if inst.level})
    logger.info(f"[fee-preview] Available levels in DB: {available_levels}")

    total_fee = sum(float(inst.amount) for inst in installments) if installments else 0
    logger.info(f"[fee-preview] Final total_fee={total_fee}")

    return {
        "school_id": school_id,
        "level": level_norm,
        "total_fee": total_fee,
        "installments_count": len(installments),
        "available_levels": available_levels,
        "installments": [
            {
                "id": inst.id,
                "installment_name": inst.name,
                "required_amount": float(inst.amount),
                "level": inst.level,
                "due_date": inst.due_date.isoformat() if inst.due_date else None
            }
            for inst in installments
        ]
    }


@router.get("/student-payments/{payment_id}", response_model=StudentPaymentResponse)
def get_student_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """Get a specific student payment by ID"""
    institution_id = int(currentUser.institution_id)
    payment = payment_api.get_student_payment_by_id(db, payment_id, institution_id)
    
    # Students can only view their own payments
    if user_has_role(currentUser.user, "student"):
        student_id = _resolve_student_id(db, currentUser)
        if payment.student_id != student_id:
            raise ForbiddenError("You can only view your own payment records")
    
    return StudentPaymentResponse.from_model(payment)


@router.get("/student-payments/status/me", response_model=StudentPaymentStatusResponse)
def get_my_payment_status(
    school_id: Optional[int] = None,
    level: Optional[str] = None,
    academic_year_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """Get current student's payment status"""
    if not user_has_role(currentUser.user, "student"):
        raise ForbiddenError("This endpoint is only for students")

    institution_id = int(currentUser.institution_id)
    student_row = resolve_student_for_logged_in_user(db, currentUser.user)
    if not student_row:
        raise NotFoundError("Student record not found for current user")
    student_id = student_row.id

    effective_year_id = academic_year_id or student_row.academic_year_id
    academic_year_name = get_academic_year_name(db, institution_id, effective_year_id)
    effective_school_id = school_id or student_row.school_id
    effective_level = (
        resolve_program_fee_level(student_row)
        or resolve_program_fee_level(student_row, fee_level=level)
        or level
    )

    return payment_api.get_payment_status(
        db,
        student_id,
        institution_id,
        effective_school_id,
        effective_level,
        academic_year=academic_year_name,
        academic_year_id=effective_year_id,
    )


@router.get("/students/{student_id}/payment-status", response_model=StudentPaymentStatusResponse)
def get_student_payment_status(
    student_id: int,
    school_id: Optional[int] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """Get payment status for a specific student (admin only)"""
    institution_id = int(currentUser.institution_id)
    
    if _is_student_only(currentUser):
        raise ForbiddenError("Only admins can view other students' payment status")
    
    return payment_api.get_payment_status(db, student_id, institution_id, school_id, level)


@router.post("/student-payments", response_model=StudentPaymentResponse, status_code=201)
def create_student_payment(
    payment_data: StudentPaymentCreate,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """
    Create a new student payment record.
    Automatically creates installments from school fee settings.
    """
    institution_id = int(currentUser.institution_id)
    
    if _is_student_only(currentUser):
        raise ForbiddenError("Only admins can create payment records")
    
    payment = payment_api.create_student_payment(db, institution_id, payment_data)
    return StudentPaymentResponse.from_model(payment)


@router.put("/student-payments/{payment_id}", response_model=StudentPaymentResponse)
def update_student_payment(
    payment_id: int,
    payment_data: StudentPaymentUpdate,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """Update a student payment record"""
    institution_id = int(currentUser.institution_id)
    
    if _is_student_only(currentUser):
        raise ForbiddenError("Only admins can update payment records")
    
    payment = payment_api.update_student_payment(db, payment_id, institution_id, payment_data)
    return StudentPaymentResponse.from_model(payment)


@router.delete("/student-payments/{payment_id}")
def delete_student_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """Delete a student payment record (admin only)"""
    institution_id = int(currentUser.institution_id)
    
    if _is_student_only(currentUser):
        raise ForbiddenError("Only admins can delete payment records")
    
    payment_api.delete_student_payment(db, payment_id, institution_id)
    return {"message": "Payment record deleted successfully"}


@router.post("/student-payments/record-payment", response_model=StudentPaymentResponse)
def record_payment(
    payment_request: RecordPaymentRequest,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """
    Record payment for student payment installments.
    Updates both installment and overall payment status.
    """
    institution_id = int(currentUser.institution_id)
    
    if _is_student_only(currentUser):
        raise ForbiddenError("Only admins can record payments")
    
    payment = payment_api.record_payment(db, institution_id, payment_request)
    return StudentPaymentResponse.from_model(payment)


@router.get("/students/{student_id}/payment-check")
def check_student_payment(
    student_id: int,
    school_id: int,
    level: str,
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
):
    """
    Check if a student has fully paid their fees.
    Used to restrict access to results/transcripts.
    """
    institution_id = int(currentUser.institution_id)
    
    is_paid = payment_api.is_student_fully_paid(db, student_id, institution_id, school_id, level)
    has_overdue = payment_api.has_overdue_payments(db, student_id, institution_id, school_id, level)
    
    return {
        "student_id": student_id,
        "school_id": school_id,
        "level": level,
        "is_fully_paid": is_paid,
        "has_overdue_payments": has_overdue,
        "can_access_results": is_paid,
        "message": "Student has fully paid" if is_paid else "Student has outstanding payments"
    }
