"""
Student Payment Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StudentPaymentInstallmentBase(BaseModel):
    installment_name: str = Field(..., min_length=1, max_length=255)
    required_amount: float = Field(..., ge=0)
    due_date: str = Field(..., description="Due date (YYYY-MM-DD)")


class StudentPaymentInstallmentCreate(StudentPaymentInstallmentBase):
    pass


class StudentPaymentInstallmentResponse(BaseModel):
    id: int
    student_payment_id: int
    student_id: int
    school_id: int
    installment_name: str
    required_amount: float
    paid_amount: float
    due_date: datetime
    due_date_formatted: Optional[str] = None
    is_paid: int
    payment_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, installment):
        due_date_str = installment.due_date.strftime('%Y-%m-%d') if installment.due_date else None
        return cls(
            id=installment.id,
            student_payment_id=installment.student_payment_id,
            student_id=installment.student_id,
            school_id=installment.school_id,
            installment_name=installment.installment_name,
            required_amount=float(installment.required_amount),
            paid_amount=float(installment.paid_amount),
            due_date=installment.due_date,
            due_date_formatted=due_date_str,
            is_paid=installment.is_paid,
            payment_date=installment.payment_date,
            created_at=installment.created_at,
            updated_at=installment.updated_at
        )


class StudentPaymentBase(BaseModel):
    student_id: int
    school_id: int
    level: str = Field(..., description="HND, DEGREE, or MASTERS")
    academic_year: Optional[str] = None


class StudentPaymentCreate(StudentPaymentBase):
    installments: Optional[List[StudentPaymentInstallmentCreate]] = []


class StudentPaymentUpdate(BaseModel):
    is_fully_paid: Optional[bool] = None
    total_fee_amount: Optional[float] = Field(None, ge=0)
    academic_year: Optional[str] = None


class StudentPaymentResponse(BaseModel):
    id: int
    student_id: int
    institution_id: int
    school_id: int
    school_name: Optional[str] = None
    level: str
    is_fully_paid: int
    total_fee_amount: float
    total_paid: float
    academic_year: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    installments: List[StudentPaymentInstallmentResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, payment):
        school_name = None
        if hasattr(payment, 'school') and payment.school:
            school_name = payment.school.name
        
        installment_list = []
        if hasattr(payment, 'installments'):
            installment_list = [StudentPaymentInstallmentResponse.from_model(i) for i in payment.installments]
        
        return cls(
            id=payment.id,
            student_id=payment.student_id,
            institution_id=payment.institution_id,
            school_id=payment.school_id,
            school_name=school_name,
            level=payment.level,
            is_fully_paid=payment.is_fully_paid,
            total_fee_amount=float(payment.total_fee_amount or 0),
            total_paid=float(payment.total_paid or 0),
            academic_year=payment.academic_year,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            last_payment_date=payment.last_payment_date,
            installments=installment_list
        )


class PaymentInstallmentRequest(BaseModel):
    installment_id: int
    paid_amount: float = Field(..., ge=0)


class RecordPaymentRequest(BaseModel):
    student_payment_id: int
    installments: List[PaymentInstallmentRequest]


class StudentPaymentStatusResponse(BaseModel):
    student_id: int
    school_id: int
    level: str
    is_fully_paid: bool
    total_fee: float
    total_paid: float
    outstanding_amount: float
    installments_paid: int
    installments_total: int
    overdue_installments: List[StudentPaymentInstallmentResponse] = []
