"""
Student Payment Model - Tracks student payments against school fee installments
"""
from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey, Index
from app.database.base import DefaultBase
import datetime


class StudentPayment(DefaultBase):
    """Tracks student payments against school fee installments"""
    __tablename__ = "student_payments"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False, index=True)  # Reference to student (users table)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    school_id = Column(Integer, nullable=False, index=True)  # School the student belongs to
    level = Column(String(20), nullable=False)  # HND, DEGREE, MASTERS
    
    # Payment status
    is_fully_paid = Column(Integer, default=0, nullable=False)  # 0 = not paid, 1 = fully paid
    total_fee_amount = Column(Numeric(10, 2), nullable=True, default=0)  # Total fee for this student's level
    total_paid = Column(Numeric(10, 2), nullable=True, default=0)  # Total amount paid
    
    # Academic year tracking
    academic_year = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    last_payment_date = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('ix_student_payments_student_school_level', 'student_id', 'school_id', 'level', unique=True),
    )


class StudentPaymentInstallment(DefaultBase):
    """Tracks individual installment payments for students"""
    __tablename__ = "student_payment_installments"

    id = Column(Integer, primary_key=True)
    student_payment_id = Column(Integer, ForeignKey('student_payments.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, nullable=False, index=True)
    institution_id = Column(Integer, nullable=False, index=True)
    school_id = Column(Integer, nullable=False, index=True)
    
    # Installment details
    installment_name = Column(String(255), nullable=False)  # e.g., "First Installment", "Registration Fee"
    required_amount = Column(Numeric(10, 2), nullable=False)  # Amount that was required
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)  # Amount paid
    due_date = Column(DateTime, nullable=False)  # Original due date
    is_paid = Column(Integer, default=0, nullable=False)  # 0 = not paid, 1 = paid
    payment_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)

    __table_args__ = (
        Index('ix_student_payment_installments_student', 'student_id'),
    )
