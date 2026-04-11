"""
Fee Structure Model - Stores fee settings and installments per school/tenant
"""
from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey, Index, Boolean
from app.database.base import DefaultBase
import datetime


class FeeStructure(DefaultBase):
    """Fee Structure model - stores fee settings per tenant/institution"""
    
    __tablename__ = "fee_structures"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)  # Reference to tenant/institution
    fee_amount = Column(Numeric(10, 2), nullable=True, default=0)  # Total fee amount
    fee_deadline = Column(DateTime, nullable=True)  # Final payment deadline
    academic_year = Column(String(50), nullable=True)  # e.g., "2024-2025"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    
    __table_args__ = (
        Index('ix_fee_structure_tenant', 'tenant_id'),
    )


class FeeInstallment(DefaultBase):
    """Fee Installment model - stores individual payment installments per school and level"""
    
    __tablename__ = "fee_installments"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)  # Reference to tenant/institution
    school_id = Column(Integer, nullable=False, index=True)  # Reference to school (Engineering, Business, etc.)
    level = Column(String(20), nullable=False)  # HND, DEGREE, MASTERS
    name = Column(String(255), nullable=False)  # e.g., "First Installment", "Registration Fee"
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(DateTime, nullable=False)
    order_index = Column(Integer, nullable=True, default=0)  # For ordering installments
    is_active = Column(Boolean, default=True, nullable=False)  # True = active, False = inactive
    is_due = Column(Boolean, default=False, nullable=False)  # True = due date has arrived
    is_overdue = Column(Boolean, default=False, nullable=False)  # True = past due date
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    
    __table_args__ = (
        Index('ix_fee_installment_tenant', 'tenant_id'),
        Index('ix_fee_installment_school', 'school_id'),
        Index('ix_fee_installment_due_date', 'due_date'),
        Index('ix_fee_installment_school_level', 'school_id', 'level'),
    )
