"""
School and School Fee Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================
# School Schemas
# ============================================

class SchoolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class SchoolCreate(SchoolBase):
    pass


class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class SchoolResponse(SchoolBase):
    id: int
    institution_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# Level Enum
# ============================================

class FeeLevel(str):
    HND = "HND"
    DEGREE = "DEGREE"
    MASTERS = "MASTERS"


# ============================================
# School Fee Schemas (fee per school + level)
# ============================================

class SchoolFeeBase(BaseModel):
    school_id: int
    level: str = Field(..., description="Fee level: HND, DEGREE, or MASTERS")
    fee_amount: float = Field(..., ge=0, description="Fee amount for this school + level")
    fee_deadline: Optional[str] = Field(None, description="Payment deadline (YYYY-MM-DD)")


class SchoolFeeCreate(BaseModel):
    school_id: int
    level: str
    fee_amount: float
    fee_deadline: Optional[str] = None
    academic_year_id: Optional[int] = Field(None, description="Academic year for this fee row")


class SchoolFeeUpdate(BaseModel):
    fee_amount: Optional[float] = Field(None, ge=0)
    fee_deadline: Optional[str] = None
    academic_year_id: Optional[int] = None


class SchoolFeeResponse(BaseModel):
    id: int
    school_id: int
    school_name: Optional[str] = None
    school_code: Optional[str] = None
    level: str
    academic_year_id: Optional[int] = None
    academic_year_name: Optional[str] = None
    fee_amount: float
    fee_deadline: Optional[datetime] = None
    fee_deadline_formatted: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, fee, academic_year_name: Optional[str] = None):
        deadline_str = fee.fee_deadline.strftime('%Y-%m-%d') if fee.fee_deadline else None
        school_name = None
        school_code = None
        if hasattr(fee, 'school') and fee.school:
            school_name = fee.school.name
            school_code = fee.school.code
        return cls(
            id=fee.id,
            school_id=fee.school_id,
            school_name=school_name,
            school_code=school_code,
            level=fee.level,
            academic_year_id=getattr(fee, "academic_year_id", None),
            academic_year_name=academic_year_name,
            fee_amount=float(fee.fee_amount),
            fee_deadline=fee.fee_deadline,
            fee_deadline_formatted=deadline_str,
            created_at=fee.created_at,
            updated_at=fee.updated_at
        )


# ============================================
# School with Fees Response
# ============================================

class SchoolWithFeesResponse(SchoolBase):
    id: int
    institution_id: int
    fees: List[SchoolFeeResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
