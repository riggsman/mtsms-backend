"""
Student Payment API - CRUD operations for student payments and installments

NOTE: School and SchoolFee models are disabled as their tables were dropped by migrations.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.student_payment import StudentPayment, StudentPaymentInstallment
# from app.models.school import School, SchoolFee  # Disabled - tables dropped
from app.schemas.student_payment import (
    StudentPaymentCreate,
    StudentPaymentUpdate,
    StudentPaymentResponse,
    RecordPaymentRequest,
    StudentPaymentStatusResponse,
    StudentPaymentInstallmentResponse
)
from app.exceptions import NotFoundError, ValidationError


VALID_LEVELS = ["HND", "DEGREE", "MASTERS"]


def get_student_payment(
    db: Session,
    student_id: int,
    institution_id: int,
    school_id: Optional[int] = None,
    level: Optional[str] = None
) -> Optional[StudentPayment]:
    """Get student payment record"""
    query = db.query(StudentPayment).filter(
        StudentPayment.student_id == student_id,
        StudentPayment.institution_id == institution_id
    )
    
    if school_id:
        query = query.filter(StudentPayment.school_id == school_id)
    if level:
        query = query.filter(StudentPayment.level == level.upper())
    
    return query.first()


def get_student_payment_by_id(
    db: Session,
    payment_id: int,
    institution_id: int
) -> StudentPayment:
    """Get a student payment by ID"""
    payment = db.query(StudentPayment).filter(
        StudentPayment.id == payment_id,
        StudentPayment.institution_id == institution_id
    ).first()
    
    if not payment:
        raise NotFoundError(f"Student payment with ID {payment_id} not found")
    return payment


def get_student_payments(
    db: Session,
    institution_id: int,
    student_id: Optional[int] = None,
    school_id: Optional[int] = None
) -> List[StudentPayment]:
    """Get all student payments for an institution"""
    query = db.query(StudentPayment).filter(
        StudentPayment.institution_id == institution_id
    )
    
    if student_id:
        query = query.filter(StudentPayment.student_id == student_id)
    if school_id:
        query = query.filter(StudentPayment.school_id == school_id)
    
    return query.order_by(StudentPayment.created_at.desc()).all()


def create_student_payment(
    db: Session,
    institution_id: int,
    payment_data: StudentPaymentCreate
) -> StudentPayment:
    """Create a new student payment record with installments from school fee settings"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[create_student_payment] institution_id={institution_id}, school_id={payment_data.school_id}, level={payment_data.level}")
    
    # Validate level
    level = payment_data.level.upper()
    if level not in VALID_LEVELS:
        raise ValidationError(f"Level must be one of: {', '.join(VALID_LEVELS)}")
    
    # Check if payment record already exists for this student/school/level
    existing = get_student_payment(
        db, payment_data.student_id, institution_id,
        payment_data.school_id, level
    )
    
    if existing:
        raise ValidationError(
            f"Payment record already exists for student {payment_data.student_id} "
            f"at {level} level"
        )
    
    # Get total fee from fee_installments table
    from app.models.fee_structure import FeeInstallment
    total_fee = 0
    fee_source = None
    
    # Filter by tenant_id (institution_id), school_id, and specific level
    installments = db.query(FeeInstallment).filter(
        FeeInstallment.tenant_id == institution_id,
        FeeInstallment.school_id == payment_data.school_id,
        FeeInstallment.level == level,
        FeeInstallment.is_active == True
    ).all()
    
    logger.info(f"[create_student_payment] Level {level}: Found {len(installments)} installments for school={payment_data.school_id}")
    if installments:
        fee_source = f"Exact match for {level}"
        total_fee = sum(float(inst.amount) for inst in installments)
    
    # If no specific level found, try without tenant filter but with level
    if not installments:
        installments = db.query(FeeInstallment).filter(
            FeeInstallment.school_id == payment_data.school_id,
            FeeInstallment.level == level,
            FeeInstallment.is_active == True
        ).all()
        logger.info(f"[create_student_payment] Fallback 1: Found {len(installments)} installments without tenant filter")
        if installments:
            fee_source = f"Fallback: {level} (no tenant filter)"
            total_fee = sum(float(inst.amount) for inst in installments)
    
    # Last fallback: all active installments for this school (show warning!)
    if not installments:
        all_school_instals = db.query(FeeInstallment).filter(
            FeeInstallment.school_id == payment_data.school_id,
            FeeInstallment.is_active == True
        ).all()
        
        # Show what levels are available
        available_levels = list(set([inst.level for inst in all_school_instals]))
        logger.warning(f"[create_student_payment] No {level} fee found! Available levels: {available_levels}")
        
        # Use whatever is available
        if all_school_instals:
            installments = all_school_instals
            fee_source = f"WARNING: Using all levels (no {level} specific fee) - available: {available_levels}"
            total_fee = sum(float(inst.amount) for inst in installments)
            logger.warning(f"[create_student_payment] Using fallback fee: {total_fee} from {len(installments)} installments")
    
    if installments:
        logger.info(f"[create_student_payment] Fee source: {fee_source}, Total fee: {total_fee}")
    
    # Create student payment record
    student_payment = StudentPayment(
        student_id=payment_data.student_id,
        institution_id=institution_id,
        school_id=payment_data.school_id,
        level=level,
        academic_year=payment_data.academic_year,
        total_fee_amount=total_fee,
        total_paid=0,
        is_fully_paid=0
    )
    db.add(student_payment)
    db.flush()  # Get the ID
    
    # Create installment records from fee_installments
    if installments:
        for inst in installments:
            installment = StudentPaymentInstallment(
                student_payment_id=student_payment.id,
                student_id=payment_data.student_id,
                institution_id=institution_id,
                school_id=payment_data.school_id,
                installment_name=inst.name or f"Installment",
                required_amount=inst.amount,
                paid_amount=0,
                due_date=inst.due_date or datetime.utcnow(),
                is_paid=0
            )
            db.add(installment)
    elif total_fee > 0:
        # If no installment setup, create a single "Full Payment" installment
        due_date = datetime.utcnow()
        installment = StudentPaymentInstallment(
            student_payment_id=student_payment.id,
            student_id=payment_data.student_id,
            institution_id=institution_id,
            school_id=payment_data.school_id,
            installment_name="Full Payment",
            required_amount=total_fee,
            paid_amount=0,
            due_date=due_date,
            is_paid=0
        )
        db.add(installment)
    
    db.commit()
    db.refresh(student_payment)
    
    return student_payment


def update_student_payment(
    db: Session,
    payment_id: int,
    institution_id: int,
    payment_data: StudentPaymentUpdate
) -> StudentPayment:
    """Update a student payment"""
    payment = get_student_payment_by_id(db, payment_id, institution_id)
    
    data = payment_data.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "is_fully_paid":
            setattr(payment, k, 1 if v else 0)
        else:
            setattr(payment, k, v)
    
    db.commit()
    db.refresh(payment)
    return payment


def delete_student_payment(db: Session, payment_id: int, institution_id: int) -> bool:
    """Delete a student payment (cascades to installments)"""
    payment = get_student_payment_by_id(db, payment_id, institution_id)
    db.delete(payment)
    db.commit()
    return True


def record_payment(
    db: Session,
    institution_id: int,
    payment_request: RecordPaymentRequest
) -> StudentPayment:
    """Record payment for one or more installments"""
    payment = get_student_payment_by_id(db, payment_request.student_payment_id, institution_id)
    
    total_paid = float(payment.total_paid or 0)
    
    for inst_request in payment_request.installments:
        installment = db.query(StudentPaymentInstallment).filter(
            StudentPaymentInstallment.id == inst_request.installment_id,
            StudentPaymentInstallment.student_payment_id == payment.id
        ).first()
        
        if not installment:
            raise NotFoundError(f"Installment with ID {inst_request.installment_id} not found")
        
        # Update installment
        installment.paid_amount = inst_request.paid_amount
        installment.is_paid = 1
        installment.payment_date = datetime.utcnow()
        
        total_paid += inst_request.paid_amount
    
    # Update payment totals
    payment.total_paid = total_paid
    payment.last_payment_date = datetime.utcnow()
    
    # Check if fully paid
    total_fee = float(payment.total_fee_amount or 0)
    if total_paid >= total_fee:
        payment.is_fully_paid = 1
    else:
        payment.is_fully_paid = 0
    
    db.commit()
    db.refresh(payment)
    
    return payment


def get_payment_status(
    db: Session,
    student_id: int,
    institution_id: int,
    school_id: Optional[int] = None,
    level: Optional[str] = None
) -> StudentPaymentStatusResponse:
    """Get payment status for a student"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Normalize level to uppercase for consistent matching
    level_norm = level.upper() if level else None
    logger.info(f"[get_payment_status] student_id={student_id}, school_id={school_id}, level={level} -> normalized={level_norm}")
    
    payment = get_student_payment(db, student_id, institution_id, school_id, level_norm)
    logger.info(f"[get_payment_status] Found payment: {payment.id if payment else None}, level={payment.level if payment else None}")
    
    if not payment:
        return StudentPaymentStatusResponse(
            student_id=student_id,
            school_id=school_id or 0,
            level=level or "",
            is_fully_paid=False,
            total_fee=0,
            total_paid=0,
            outstanding_amount=0,
            installments_paid=0,
            installments_total=0,
            overdue_installments=[]
        )
    
    # Load installments
    installments = db.query(StudentPaymentInstallment).filter(
        StudentPaymentInstallment.student_payment_id == payment.id
    ).all()
    
    # Find overdue installments
    now = datetime.utcnow()
    overdue = [
        StudentPaymentInstallmentResponse.from_model(i)
        for i in installments
        if not i.is_paid and i.due_date < now
    ]
    
    installments_paid = sum(1 for i in installments if i.is_paid)
    
    return StudentPaymentStatusResponse(
        student_id=student_id,
        school_id=payment.school_id,
        level=payment.level,
        is_fully_paid=bool(payment.is_fully_paid),
        total_fee=float(payment.total_fee_amount or 0),
        total_paid=float(payment.total_paid or 0),
        outstanding_amount=float(payment.total_fee_amount or 0) - float(payment.total_paid or 0),
        installments_paid=installments_paid,
        installments_total=len(installments),
        overdue_installments=overdue
    )


def is_student_fully_paid(
    db: Session,
    student_id: int,
    institution_id: int,
    school_id: int,
    level: str
) -> bool:
    """Check if a student has fully paid their fees"""
    payment = get_student_payment(db, student_id, institution_id, school_id, level)
    
    if not payment:
        return False
    
    return bool(payment.is_fully_paid)


def has_overdue_payments(
    db: Session,
    student_id: int,
    institution_id: int,
    school_id: int,
    level: str
) -> bool:
    """Check if a student has overdue installment payments"""
    payment = get_student_payment(db, student_id, institution_id, school_id, level)
    
    if not payment:
        return False
    
    now = datetime.utcnow()
    overdue = db.query(StudentPaymentInstallment).filter(
        StudentPaymentInstallment.student_payment_id == payment.id,
        StudentPaymentInstallment.is_paid == 0,
        StudentPaymentInstallment.due_date < now
    ).first()
    
    return overdue is not None


def apply_completed_online_payment(db: Session, payment_row) -> None:
    """
    After a mobile-money Payment is verified (status=paid), allocate the amount
    toward StudentPayment installments when a fee plan exists for the student's school/level.
    """
    from app.models.payment import Payment
    from app.models.student import Student

    if not isinstance(payment_row, Payment):
        return
    if payment_row.status != "paid":
        return

    student = (
        db.query(Student)
        .filter(Student.id == payment_row.student_id, Student.deleted_at.is_(None))
        .first()
    )
    if not student or not student.school_id:
        return

    level = (student.level or "").strip().upper()
    if level not in VALID_LEVELS:
        return

    sp = get_student_payment(
        db,
        payment_row.student_id,
        payment_row.institution_id,
        student.school_id,
        level,
    )
    if not sp:
        return

    remaining = float(payment_row.amount or 0)
    if remaining <= 0:
        return

    installments = (
        db.query(StudentPaymentInstallment)
        .filter(StudentPaymentInstallment.student_payment_id == sp.id)
        .order_by(
            StudentPaymentInstallment.due_date.asc(),
            StudentPaymentInstallment.id.asc(),
        )
        .all()
    )

    if not installments:
        paid_so_far = float(sp.total_paid or 0)
        sp.total_paid = paid_so_far + remaining
        sp.last_payment_date = datetime.utcnow()
        tf = float(sp.total_fee_amount or 0)
        if tf > 0 and float(sp.total_paid or 0) >= tf - 0.01:
            sp.is_fully_paid = 1
        db.commit()
        return

    for inst in installments:
        if remaining <= 0:
            break
        required = float(inst.required_amount or 0)
        already_paid = float(inst.paid_amount or 0)
        if inst.is_paid and already_paid >= required - 0.01:
            continue
        owed = max(0.0, required - already_paid)
        if owed <= 0:
            continue
        chunk = min(owed, remaining)
        inst.paid_amount = already_paid + chunk
        if inst.paid_amount >= required - 0.01:
            inst.is_paid = 1
            inst.payment_date = datetime.utcnow()
        remaining -= chunk

    total_from_installments = sum(float(i.paid_amount or 0) for i in installments)
    if remaining > 0:
        total_from_installments += remaining

    sp.total_paid = total_from_installments
    sp.last_payment_date = datetime.utcnow()
    tf = float(sp.total_fee_amount or 0)
    if tf > 0 and total_from_installments >= tf - 0.01:
        sp.is_fully_paid = 1
    else:
        sp.is_fully_paid = 0

    db.commit()
