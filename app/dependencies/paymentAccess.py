"""
Payment Access Dependencies - Check if students have paid fees before accessing results/transcripts
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.sessionManager import get_db
from app.authentication.authenticator import auth_guard, AuthUser
from app.apis.student_payment import is_student_fully_paid, has_overdue_payments
from app.models.student import Student


class PaymentAccessError(HTTPException):
    """Custom exception for payment access restrictions"""
    def __init__(self, message: str, school_id: int = None, level: str = None):
        detail = {
            "message": message,
            "error": "payment_required",
            "school_id": school_id,
            "level": level,
            "action_required": "Please complete your fee payments to access this resource."
        }
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_student_school_level(
    db: Session,
    student_id: int,
    institution_id: int
) -> tuple:
    """
    Get student's school_id and level from their student record.
    Returns (school_id, level) or raises HTTPException if not found.
    """
    student = db.query(Student).filter(
        Student.user_id == student_id,
        Student.institution_id == institution_id
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student record not found"
        )
    
    school_id = getattr(student, 'school_id', None)
    level = getattr(student, 'level', None)
    
    if not school_id or not level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student record is missing school or level information. Please contact administration."
        )
    
    return school_id, level


async def check_payment_access(
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
) -> dict:
    """
    Dependency that checks if a student has fully paid their fees.
    Returns a dict with payment status info.
    Raises PaymentAccessError if student has not paid.
    
    Usage:
        @router.get("/results")
        async def get_results(
            payment_status: dict = Depends(check_payment_access)
        ):
            ...
    """
    if currentUser.role != "student":
        return {
            "has_access": True,
            "is_admin": True,
            "student_id": None,
            "school_id": None,
            "level": None
        }
    
    institution_id = int(currentUser.institution_id)
    student_id = currentUser.user_id
    
    school_id, level = await get_student_school_level(db, student_id, institution_id)
    
    is_paid = is_student_fully_paid(db, student_id, institution_id, school_id, level)
    has_overdue = has_overdue_payments(db, student_id, institution_id, school_id, level)
    
    if not is_paid:
        if has_overdue:
            raise PaymentAccessError(
                message=f"Access denied: You have overdue fee payments for your {level} program. "
                        f"Please clear your outstanding fees to access results and transcripts.",
                school_id=school_id,
                level=level
            )
        else:
            raise PaymentAccessError(
                message=f"Access denied: Your fees for the {level} program are not fully paid. "
                        f"Please complete your payment to access results and transcripts.",
                school_id=school_id,
                level=level
            )
    
    return {
        "has_access": True,
        "is_admin": False,
        "student_id": student_id,
        "school_id": school_id,
        "level": level
    }


async def optional_payment_check(
    db: Session = Depends(get_db),
    currentUser: AuthUser = Depends(auth_guard)
) -> dict:
    """
    Optional payment check - returns payment status but doesn't block access.
    Useful for showing payment status UI without restricting access.
    
    Returns:
        dict with has_access, is_fully_paid, overdue_installments, etc.
    """
    if currentUser.role != "student":
        return {
            "has_access": True,
            "is_admin": True,
            "is_fully_paid": None,
            "has_overdue": None,
            "student_id": None
        }
    
    institution_id = int(currentUser.institution_id)
    student_id = currentUser.user_id
    
    try:
        school_id, level = await get_student_school_level(db, student_id, institution_id)
    except HTTPException:
        return {
            "has_access": True,
            "is_admin": False,
            "is_fully_paid": None,
            "has_overdue": None,
            "student_id": student_id,
            "error": "Student record not found"
        }
    
    is_paid = is_student_fully_paid(db, student_id, institution_id, school_id, level)
    has_overdue = has_overdue_payments(db, student_id, institution_id, school_id, level)
    
    return {
        "has_access": is_paid,
        "is_admin": False,
        "is_fully_paid": is_paid,
        "has_overdue": has_overdue,
        "student_id": student_id,
        "school_id": school_id,
        "level": level
    }


def require_payment_access():
    """
    Decorator-style dependency for routes that require payment access.
    Use as: Depends(require_payment_access())
    
    This allows the dependency to be used in routes that need payment verification
    while still being optional for admin routes.
    """
    return check_payment_access


def require_admin_or_payment():
    """
    Dependency that allows admin access without payment check,
    but requires payment for students.
    """
    async def dependency(
        db: Session = Depends(get_db),
        currentUser: AuthUser = Depends(auth_guard)
    ):
        if currentUser.role != "student":
            return {
                "has_access": True,
                "is_admin": True,
                "student_id": None
            }
        
        institution_id = int(currentUser.institution_id)
        student_id = currentUser.user_id
        
        school_id, level = await get_student_school_level(db, student_id, institution_id)
        
        is_paid = is_student_fully_paid(db, student_id, institution_id, school_id, level)
        
        if not is_paid:
            raise PaymentAccessError(
                message=f"Payment required to access this resource",
                school_id=school_id,
                level=level
            )
        
        return {
            "has_access": True,
            "is_admin": False,
            "student_id": student_id,
            "school_id": school_id,
            "level": level
        }
    
    return dependency
