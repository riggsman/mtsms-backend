"""
Payment Routes - FastAPI endpoints for payment operations
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PaymentResponse,
    PaymentListResponse
)
from app.apis.payments import (
    initiate_payment,
    verify_payment,
    get_payment,
    get_payment_by_receipt,
    get_payments,
    get_student_payments,
    update_payment,
    delete_payment
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

payment = APIRouter()


@payment.post("/payments/initiate", response_model=PaymentInitiateResponse, status_code=201)
def initiate_payment_endpoint(
    payment_data: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
):
    """
    Initiate a payment - sends OTP to student email
    Students can initiate their own payments
    """
    # Students can only initiate payments for themselves
    if current_user.role == UserRole.STUDENT.value:
        # Verify the payment is for the current student
        from app.models.student import Student
        student = db.query(Student).filter(
            Student.email == current_user.email,
            Student.institution_id == current_user.institution_id,
            Student.deleted_at.is_(None)
        ).first()
        
        if not student or student.id != payment_data.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only initiate payments for themselves"
            )
    
    # Get institution_id
    final_institution_id = institution_id or current_user.institution_id
    if not final_institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="institution_id is required"
        )
    
    return initiate_payment(
        db=db,
        payment_request=payment_data,
        current_user=current_user,
        institution_id=final_institution_id
    )


@payment.post("/payments/verify", response_model=PaymentVerifyResponse)
def verify_payment_endpoint(
    verify_data: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
):
    """
    Verify payment with OTP and complete the transaction
    Students can verify their own payments
    """
    # Get institution_id
    final_institution_id = institution_id or current_user.institution_id
    
    # Verify payment
    result = verify_payment(
        db=db,
        verify_request=verify_data,
        current_user=current_user,
        institution_id=final_institution_id
    )
    
    # Students can only verify their own payments
    if current_user.role == UserRole.STUDENT.value:
        if result.payment.student_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only verify their own payments"
            )
    
    return result


@payment.get("/payments/my", response_model=PaginatedResponse[PaymentResponse])
def get_my_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get current user's payments (for students)
    """
    if current_user.role != UserRole.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for students"
        )
    
    # Get student by email
    from app.models.student import Student
    student = db.query(Student).filter(
        Student.email == current_user.email,
        Student.institution_id == current_user.institution_id,
        Student.deleted_at.is_(None)
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student record not found for current user"
        )
    
    skip = (page - 1) * page_size
    payments, total = get_student_payments(
        db=db,
        student_id=student.id,
        skip=skip,
        limit=page_size,
        institution_id=current_user.institution_id
    )
    
    # Convert payments to response format
    payment_responses = [PaymentResponse.from_payment(p) for p in payments]
    
    # Filter by status if provided
    if status:
        payment_responses = [p for p in payment_responses if p.status == status.lower()]
        total = len(payment_responses)
    
    return PaginatedResponse.create(
        items=payment_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@payment.get("/payments/receipt/{receipt_number}", response_model=PaymentResponse)
def get_receipt_endpoint(
    receipt_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get payment by receipt number
    Students can only view their own receipts
    """
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    payment = get_payment_by_receipt(
        db=db,
        receipt_number=receipt_number,
        institution_id=institution_id
    )
    
    # Students can only view their own receipts
    if current_user.role == UserRole.STUDENT.value:
        if payment.student_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own receipts"
            )
    
    return PaymentResponse.from_payment(payment)


@payment.get("/payments", response_model=PaginatedResponse[PaymentResponse])
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    student_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    x_institution_id: Optional[str] = Header(default=None, alias="X-Institution-Id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """
    Get list of payments with pagination (Admin/Staff only)
    """
    skip = (page - 1) * page_size
    
    # Validate institution_id
    is_system_admin = current_user.role and current_user.role.startswith('system_')
    institution_id = None
    
    if is_system_admin:
        if x_institution_id:
            try:
                institution_id = int(x_institution_id)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid institution_id format: {x_institution_id}"
                )
    else:
        if not current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to view payments"
            )
        
        if x_institution_id:
            try:
                header_institution_id = int(x_institution_id)
                if header_institution_id != current_user.institution_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Institution ID mismatch. You can only access data for your institution (ID: {current_user.institution_id})"
                    )
                institution_id = header_institution_id
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid institution_id format: {x_institution_id}"
                )
        else:
            institution_id = current_user.institution_id
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {start_date}. Use ISO format."
            )
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format: {end_date}. Use ISO format."
            )
    
    payments, total = get_payments(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        student_id=student_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt
    )
    
    return PaginatedResponse.create(
        items=payments,
        total=total,
        page=page,
        page_size=page_size
    )


@payment.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get a payment by ID
    Students can only view their own payments
    """
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    payment = get_payment(db=db, payment_id=payment_id, institution_id=institution_id)
    
    # Students can only view their own payments
    if current_user.role == UserRole.STUDENT.value:
        if payment.student_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own payments"
            )
    
    return PaymentResponse.from_payment(payment)


@payment.put("/payments/{payment_id}", response_model=PaymentResponse)
def update_payment_endpoint(
    payment_id: int,
    status: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """
    Update a payment (Admin/Staff only)
    """
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    updated_payment = update_payment(
        db=db,
        payment_id=payment_id,
        status=status,
        description=description,
        current_user=current_user,
        institution_id=institution_id
    )
    
    return PaymentResponse.from_payment(updated_payment)


@payment.delete("/payments/{payment_id}", status_code=204)
def delete_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Delete a payment (soft delete) - Admin/Super Admin only
    """
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    delete_payment(db=db, payment_id=payment_id, current_user=current_user, institution_id=institution_id)
    return None
