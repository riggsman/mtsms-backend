"""
Payment Routes - FastAPI endpoints for payment operations
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.exceptions.exceptions import ForbiddenError
from app.helpers.logger import logger
from app.database.base import get_db_session

from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PaymentResponse,
    PaymentListResponse,
    PaymentPublicVerificationResponse,
)
from app.apis.payments import (
    initiate_payment,
    verify_payment,
    get_payment,
    get_payment_by_receipt,
    get_payments,
    get_student_payments,
    update_payment,
    delete_payment,
    payment_to_response,
    payments_to_responses,
    get_public_payment_verification,
    cancel_student_pending_payment,
)
from app.apis.students import resolve_student_for_logged_in_user
from app.dependencies.tenantDependency import get_db, get_tenant
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse
from app.helpers.user_roles import user_has_role, user_is_system_admin, user_requires_tenant_scope_for_data

payment = APIRouter()


@payment.get(
    "/payments/public/verify/{transaction_id}",
    response_model=PaymentPublicVerificationResponse,
)
def public_payment_verification(
    transaction_id: str,
    institution_id: int = Query(
        ...,
        ge=1,
        description="Institution ID (tenant) — required with transaction_id for verification",
    ),
    db: Session = Depends(get_db_session),
):
    """
    Public payment verification (no authentication).
    Intended for QR codes on receipts; returns the same payment fields as the receipt view.
    """
    return get_public_payment_verification(db, transaction_id, institution_id)


@payment.post("/payments/initiate", response_model=PaymentInitiateResponse, status_code=201)
def initiate_payment_endpoint(
    payment_data: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
    institution_id: Optional[int] = Depends(get_institution_id_from_header),
    tenant_name: Optional[str] = Depends(get_tenant),
):
    """
    Initiate a payment - sends OTP to student email
    Students can initiate their own payments
    """
    # Students can only initiate payments for their own student record (same resolver as /students/me)
    if user_has_role(current_user, UserRole.STUDENT.value):
        student = resolve_student_for_logged_in_user(db, current_user)
        if not student or student.id != payment_data.student_id:
            raise ForbiddenError(
                "Students can only initiate payments for their own student account."
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
        institution_id=final_institution_id,
        tenant_name=tenant_name,
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
    if user_has_role(current_user, UserRole.STUDENT.value):
        me = resolve_student_for_logged_in_user(db, current_user)
        if not me or me.id != result.payment.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only verify their own payments",
            )
    
    return result


@payment.get("/payments/my", response_model=PaginatedResponse[PaymentResponse])
def get_my_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get current user's payments (for students)
    """
    if not user_has_role(current_user, UserRole.STUDENT.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for students"
        )
    
    student = resolve_student_for_logged_in_user(db, current_user)

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
    
    payment_responses = payments_to_responses(db, payments)
    
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


@payment.delete("/payments/my/pending/{payment_id}", status_code=204)
def cancel_my_pending_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    """
    Student only: soft-delete own payment row when status is still **pending**
    (abandon an incomplete mobile-money / OTP flow).
    """
    if not user_has_role(current_user, UserRole.STUDENT.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can remove pending payment records",
        )
    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    cancel_student_pending_payment(
        db=db,
        payment_id=payment_id,
        current_user=current_user,
        institution_id=institution_id,
    )
    return None


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
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    
    payment = get_payment_by_receipt(
        db=db,
        receipt_number=receipt_number,
        institution_id=institution_id
    )
    
    # Students can only view their own receipts
    if user_has_role(current_user, UserRole.STUDENT.value):
        me = resolve_student_for_logged_in_user(db, current_user)
        if not me or me.id != payment.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own receipts",
            )
    
    return payment_to_response(db, payment)


@payment.get("/payments", response_model=PaginatedResponse[PaymentResponse])
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
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
    is_system_admin = user_is_system_admin(current_user)
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
        items=payments_to_responses(db, payments),
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
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    
    payment = get_payment(db=db, payment_id=payment_id, institution_id=institution_id)
    
    # Students can only view their own payments
    if user_has_role(current_user, UserRole.STUDENT.value):
        me = resolve_student_for_logged_in_user(db, current_user)
        if not me or me.id != payment.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own payments",
            )

    return payment_to_response(db, payment)


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
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    
    updated_payment = update_payment(
        db=db,
        payment_id=payment_id,
        status=status,
        description=description,
        current_user=current_user,
        institution_id=institution_id
    )
    
    return payment_to_response(db, updated_payment)


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
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    
    delete_payment(db=db, payment_id=payment_id, current_user=current_user, institution_id=institution_id)
    return None
