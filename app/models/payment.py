"""
Payment Model
"""
from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey, Index, Boolean
from app.database.sessionManager import BaseModel_Base
import datetime
import uuid


class Payment(BaseModel_Base):
    """Payment model for tracking student payments"""
    
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False, index=True)
    student_id_number = Column(String(70), nullable=False, index=True)  # Student matricule/ID
    student_name = Column(String(255), nullable=False)
    student_email = Column(String(255), nullable=False, index=True)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default='XAF', nullable=False)
    provider = Column(String(20), nullable=False)  # 'MTN' or 'ORANGE'
    reason = Column(String(255), nullable=False)  # Payment reason/type
    phone_number = Column(String(20), nullable=False)
    
    # Transaction details
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    receipt_number = Column(String(100), unique=True, nullable=True, index=True)
    
    # Status
    status = Column(String(20), default='pending', nullable=False, index=True)  # 'pending', 'paid', 'failed', 'cancelled'
    
    # Payment method (for display purposes)
    payment_method = Column(String(50), nullable=True)  # e.g., 'Mobile Money', 'Bank Transfer', 'Cash'
    description = Column(String(500), nullable=True)  # Additional description
    
    # OTP tracking
    otp_sent = Column(String(6), nullable=True)
    otp_verified = Column(Boolean, default=False, nullable=False)
    otp_sent_at = Column(DateTime, nullable=True)
    otp_verified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    paid_at = Column(DateTime, nullable=True)  # When payment was completed
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_payment_student_status', 'student_id', 'status'),
        Index('ix_payment_institution_status', 'institution_id', 'status'),
        Index('ix_payment_created', 'created_at'),
    )
