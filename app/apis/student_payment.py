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
    StudentPaymentInstallmentResponse,
    FeePaymentReceiptItem,
    FeeInstallmentPlanItem,
)
from app.helpers.program_level import normalize_program_fee_level, resolve_program_fee_level
from app.apis.fee_structure import get_installments_for_level
from app.models.payment import Payment
from app.apis.school import get_academic_year_date_bounds
from app.exceptions import NotFoundError, ValidationError


VALID_LEVELS = ["HND", "DEGREE", "MASTERS"]


def _normalize_level(level: Optional[str]) -> Optional[str]:
    if not level:
        return None
    return normalize_program_fee_level(level) or str(level).strip().upper()


def _build_plan_installments(
    db: Session,
    institution_id: int,
    school_id: int,
    level: str,
    student_payment: Optional[StudentPayment] = None,
) -> List[FeeInstallmentPlanItem]:
    """Fee catalog installments for program level, merged with student payment progress."""
    level_norm = _normalize_level(level)
    if not level_norm or not school_id:
        return []

    catalog = get_installments_for_level(db, institution_id, school_id, level_norm)
    paid_by_name: dict = {}
    if student_payment:
        rows = (
            db.query(StudentPaymentInstallment)
            .filter(StudentPaymentInstallment.student_payment_id == student_payment.id)
            .all()
        )
        for row in rows:
            key = (row.installment_name or "").strip().lower()
            if key:
                paid_by_name[key] = row

    now = datetime.utcnow()
    plan: List[FeeInstallmentPlanItem] = []
    for inst in catalog:
        key = (inst.name or "").strip().lower()
        paid_row = paid_by_name.get(key)
        due = inst.due_date
        due_str = due.strftime("%Y-%m-%d") if due else None
        is_paid = bool(paid_row and paid_row.is_paid)
        paid_amount = float(paid_row.paid_amount or 0) if paid_row else 0.0
        is_overdue = bool(due and due < now and not is_paid)
        plan.append(
            FeeInstallmentPlanItem(
                id=inst.id,
                installment_name=inst.name,
                required_amount=float(inst.amount),
                paid_amount=paid_amount,
                due_date_formatted=due_str,
                is_paid=is_paid,
                is_overdue=is_overdue,
                level=inst.level,
            )
        )
    return plan


def get_student_payment(
    db: Session,
    student_id: int,
    institution_id: int,
    school_id: Optional[int] = None,
    level: Optional[str] = None,
    academic_year: Optional[str] = None,
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
    if academic_year:
        query = query.filter(StudentPayment.academic_year == academic_year)

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
    
    level = _normalize_level(payment_data.level)
    if not level or level not in VALID_LEVELS:
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
    
    installments = get_installments_for_level(
        db, institution_id, payment_data.school_id, level
    )
    logger.info(
        f"[create_student_payment] Level {level}: Found {len(installments)} installments "
        f"for school={payment_data.school_id}"
    )
    if not installments:
        raise ValidationError(
            f"No fee installments configured for {level} at this school. "
            "Ask administration to set up installments for your program level."
        )
    total_fee = sum(float(inst.amount) for inst in installments)
    logger.info(f"[create_student_payment] Total fee from catalog: {total_fee}")
    
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


def _online_payments_for_student(
    db: Session,
    student_id: int,
    institution_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> tuple:
    """Paid and pending online payments for a student, optionally within academic year bounds."""
    from sqlalchemy import or_

    query = db.query(Payment).filter(
        Payment.student_id == student_id,
        Payment.institution_id == institution_id,
        Payment.deleted_at.is_(None),
    )
    if start_date:
        query = query.filter(
            or_(Payment.paid_at >= start_date, Payment.created_at >= start_date)
        )
    if end_date:
        query = query.filter(
            or_(Payment.paid_at <= end_date, Payment.created_at <= end_date)
        )
    rows = query.order_by(Payment.created_at.desc()).all()
    items: List[FeePaymentReceiptItem] = []
    paid_total = 0.0
    for p in rows:
        amt = float(p.amount or 0)
        if (p.status or "").lower() == "paid":
            paid_total += amt
        items.append(
            FeePaymentReceiptItem(
                id=p.id,
                receipt_number=p.receipt_number,
                amount=amt,
                status=p.status or "pending",
                reason=p.reason,
                payment_method=p.payment_method,
                provider=p.provider,
                transaction_id=p.transaction_id,
                paid_at=p.paid_at,
                created_at=p.created_at,
                currency=p.currency or "XAF",
                student_id_number=p.student_id_number,
                institution_id=p.institution_id,
            )
        )
    return items, paid_total


def get_payment_status(
    db: Session,
    student_id: int,
    institution_id: int,
    school_id: Optional[int] = None,
    level: Optional[str] = None,
    academic_year: Optional[str] = None,
    academic_year_id: Optional[int] = None,
) -> StudentPaymentStatusResponse:
    """Get payment status for a student, including online payments for the academic year."""
    import logging
    logger = logging.getLogger(__name__)

    level_norm = _normalize_level(level)
    logger.info(
        f"[get_payment_status] student_id={student_id}, school_id={school_id}, "
        f"level={level_norm}, academic_year={academic_year}, academic_year_id={academic_year_id}"
    )

    payment = get_student_payment(
        db, student_id, institution_id, school_id, level_norm, academic_year=academic_year
    )
    if not payment and academic_year:
        payment = get_student_payment(
            db, student_id, institution_id, school_id, level_norm, academic_year=None
        )

    start_dt, end_dt = get_academic_year_date_bounds(db, institution_id, academic_year_id)
    online_items, online_paid_total = _online_payments_for_student(
        db, student_id, institution_id, start_dt, end_dt
    )

    effective_school_id = school_id or (payment.school_id if payment else 0)
    plan_installments = _build_plan_installments(
        db,
        institution_id,
        effective_school_id,
        level_norm or "",
        student_payment=payment,
    )

    catalog_total = sum(i.required_amount for i in plan_installments)
    installments_paid = sum(1 for i in plan_installments if i.is_paid)
    installments_total = len(plan_installments)
    now = datetime.utcnow()

    overdue_plan = [i for i in plan_installments if i.is_overdue]
    overdue_legacy = [
        StudentPaymentInstallmentResponse(
            id=i.id,
            student_payment_id=payment.id if payment else 0,
            student_id=student_id,
            school_id=effective_school_id,
            installment_name=i.installment_name,
            required_amount=i.required_amount,
            paid_amount=i.paid_amount,
            due_date=datetime.strptime(i.due_date_formatted, "%Y-%m-%d")
            if i.due_date_formatted
            else now,
            due_date_formatted=i.due_date_formatted,
            is_paid=1 if i.is_paid else 0,
            payment_date=None,
            created_at=now,
            updated_at=None,
        )
        for i in overdue_plan
    ]

    if not payment:
        total_fee = catalog_total
        total_paid = online_paid_total
        return StudentPaymentStatusResponse(
            student_id=student_id,
            school_id=effective_school_id,
            level=level_norm or "",
            is_fully_paid=total_fee > 0 and total_paid >= total_fee,
            total_fee=total_fee,
            total_paid=total_paid,
            outstanding_amount=max(0.0, total_fee - total_paid),
            installments_paid=installments_paid,
            installments_total=installments_total,
            installments=plan_installments,
            overdue_installments=overdue_legacy,
            academic_year=academic_year,
            academic_year_id=academic_year_id,
            online_payments=online_items,
        )

    installment_paid = float(payment.total_paid or 0)
    total_paid = max(installment_paid, online_paid_total)
    total_fee = catalog_total if catalog_total > 0 else float(payment.total_fee_amount or 0)
    outstanding = max(0.0, total_fee - total_paid)
    is_fully_paid = bool(payment.is_fully_paid) or (total_fee > 0 and total_paid >= total_fee)

    return StudentPaymentStatusResponse(
        student_id=student_id,
        school_id=payment.school_id,
        level=level_norm or payment.level,
        is_fully_paid=is_fully_paid,
        total_fee=total_fee,
        total_paid=total_paid,
        outstanding_amount=outstanding,
        installments_paid=installments_paid,
        installments_total=installments_total,
        installments=plan_installments,
        overdue_installments=overdue_legacy,
        academic_year=academic_year or payment.academic_year,
        academic_year_id=academic_year_id,
        online_payments=online_items,
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

    level = resolve_program_fee_level(student)
    if not level:
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
