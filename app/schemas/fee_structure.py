"""
Fee Structure Schemas - Request/Response schemas for fee structure API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class FeeStructureUpdate(BaseModel):
    """Request schema for updating fee structure settings"""
    fee_amount: Optional[Decimal] = Field(None, ge=0, description="Total fee amount")
    fee_deadline: Optional[str] = Field(None, description="Final payment deadline (ISO format)")
    academic_year: Optional[str] = Field(None, max_length=50, description="Academic year")


class FeeStructureResponse(BaseModel):
    """Response schema for fee structure"""
    id: int
    tenant_id: int
    fee_amount: Optional[Decimal] = 0
    fee_deadline: Optional[datetime] = None
    academic_year: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FeeInstallmentCreate(BaseModel):
    """Request schema for creating a fee installment"""
    school_id: int = Field(..., description="School ID")
    level: str = Field(..., description="Level (HND, DEGREE, MASTERS)")
    name: str = Field(..., min_length=1, max_length=255, description="Installment name")
    amount: Decimal = Field(..., ge=0, description="Installment amount")
    due_date: str = Field(..., description="Due date (ISO format YYYY-MM-DD)")
    order_index: Optional[int] = Field(None, ge=0, description="Order index for display")


class FeeInstallmentUpdate(BaseModel):
    """Request schema for updating a fee installment"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Installment name")
    amount: Optional[Decimal] = Field(None, ge=0, description="Installment amount")
    due_date: Optional[str] = Field(None, description="Due date (ISO format YYYY-MM-DD)")
    order_index: Optional[int] = Field(None, ge=0, description="Order index for display")
    is_active: Optional[bool] = Field(None, description="Active status (True=active, False=inactive)")


class FeeInstallmentResponse(BaseModel):
    """Response schema for fee installment"""
    id: int
    tenant_id: int
    school_id: int
    level: str
    name: str
    amount: Decimal
    due_date: datetime
    order_index: Optional[int] = 0
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Frontend-compatible field names
    due_date_formatted: Optional[str] = None
    is_due: bool = False  # True if due date has arrived
    is_overdue: bool = False  # True if due date has passed
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_installment(cls, installment):
        """Create FeeInstallmentResponse from FeeInstallment model"""
        due_date_str = installment.due_date.strftime('%Y-%m-%d') if installment.due_date else None
        return cls(
            id=installment.id,
            tenant_id=installment.tenant_id,
            school_id=installment.school_id,
            level=installment.level,
            name=installment.name,
            amount=installment.amount,
            due_date=installment.due_date,
            order_index=installment.order_index,
            is_active=bool(installment.is_active),
            created_at=installment.created_at,
            updated_at=installment.updated_at,
            due_date_formatted=due_date_str,
            is_due=bool(installment.is_due),
            is_overdue=bool(installment.is_overdue)
        )


class FeeStructureWithInstallmentsResponse(BaseModel):
    """Response schema for fee structure with all installments"""
    id: int
    tenant_id: int
    fee_amount: Optional[Decimal] = 0
    fee_deadline: Optional[datetime] = None
    academic_year: Optional[str] = None
    installments: List[FeeInstallmentResponse] = []
    total_installment_amount: Decimal = Decimal('0')
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
