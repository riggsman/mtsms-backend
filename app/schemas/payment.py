"""
Payment Schemas
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PaymentInitiateRequest(BaseModel):
    """Request schema for initiating a payment"""
    student_id: int = Field(..., description="Student ID")
    student_email: EmailStr = Field(..., description="Student email for OTP")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    provider: str = Field(..., description="Payment provider (MTN or ORANGE)")
    reason: str = Field(..., min_length=1, max_length=255, description="Reason for payment")
    phone_number: str = Field(..., min_length=9, max_length=20, description="Phone number for payment")
    
    @validator('provider')
    def validate_provider(cls, v):
        v = v.upper()
        if v not in ['MTN', 'ORANGE']:
            raise ValueError('Provider must be either MTN or ORANGE')
        return v


class PaymentVerifyRequest(BaseModel):
    """Request schema for verifying payment with OTP"""
    transaction_id: str = Field(..., description="Transaction ID from initiate response")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class PaymentResponse(BaseModel):
    """Response schema for payment"""
    id: int
    institution_id: int
    student_id: int
    student_id_number: str
    student_name: str
    student_email: str
    amount: Decimal
    currency: str
    provider: str
    reason: str
    phone_number: str
    transaction_id: str
    receipt_number: Optional[str]
    status: str
    payment_method: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    paid_at: Optional[datetime]
    date: Optional[str] = None  # For compatibility with frontend (formatted date)
    
    # Frontend-compatible aliases (for camelCase)
    receiptNumber: Optional[str] = None
    paymentType: Optional[str] = None
    paymentMethod: Optional[str] = None
    
    @classmethod
    def from_payment(cls, payment):
        """Create PaymentResponse from Payment model"""
        # Format date for frontend
        date_str = payment.created_at.strftime('%Y-%m-%d') if payment.created_at else None
        
        # Get payment method
        payment_method = payment.payment_method or f"{payment.provider} Mobile Money"
        
        data = {
            'id': payment.id,
            'institution_id': payment.institution_id,
            'student_id': payment.student_id,
            'student_id_number': payment.student_id_number,
            'student_name': payment.student_name,
            'student_email': payment.student_email,
            'amount': payment.amount,
            'currency': payment.currency or 'XAF',
            'provider': payment.provider,
            'reason': payment.reason,
            'phone_number': payment.phone_number,
            'transaction_id': payment.transaction_id,
            'receipt_number': payment.receipt_number,
            'status': payment.status,
            'payment_method': payment_method,
            'description': payment.description or payment.reason,
            'created_at': payment.created_at,
            'updated_at': payment.updated_at,
            'paid_at': payment.paid_at,
            'date': date_str,
            # Frontend-compatible fields
            'receiptNumber': payment.receipt_number,
            'paymentType': payment.reason,  # reason maps to paymentType in frontend
            'paymentMethod': payment_method
        }
        return cls(**data)
    
    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both snake_case and camelCase


class PaymentInitiateResponse(BaseModel):
    """Response schema for payment initiation"""
    transaction_id: str
    message: str
    otp_sent: bool = True


class PaymentVerifyResponse(BaseModel):
    """Response schema for payment verification"""
    success: bool
    transaction_id: str
    receipt_number: str
    message: str
    payment: PaymentResponse


class PaymentListResponse(BaseModel):
    """Response schema for payment list"""
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
