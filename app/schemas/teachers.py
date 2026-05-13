from decimal import Decimal
from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime

class TeacherRequest(BaseModel):
    firstname: str
    middlename: Optional[str] = None
    lastname: str
    dob: str
    gender: str
    address: str
    email: str
    phone: str
    department_id: int
    # Omit or leave empty to auto-generate from Tenant Settings matricule (first segment + sequence)
    employee_id: Optional[str] = None
    position: Optional[str] = None
    designation: Optional[str] = None
    title: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    branch_id: Optional[int] = None
    institution_id: Optional[int] = None  # For tenant isolation
    username: Optional[str] = None  # Login username for linked staff user account
    hourly_rate: Optional[Decimal] = None

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def validate_hourly_rate(cls, v: Any):
        if v is None or v == "":
            return None
        d = Decimal(str(v))
        if d < 0:
            raise ValueError("hourly_rate must be >= 0")
        return d.quantize(Decimal("0.01"))

class TeacherResponse(BaseModel):
    id: int
    institution_id: int  # For tenant isolation
    firstname: str
    middlename: Optional[str]
    lastname: str
    dob: str
    gender: str
    address: str
    email: str
    phone: str
    department_id: int
    employee_id: str
    position: Optional[str] = None
    designation: Optional[str] = None
    title: Optional[str] = None
    qualification: Optional[str]
    specialization: Optional[str]
    branch_id: Optional[int] = None
    username: Optional[str] = None  # From linked User account (same email)
    hourly_rate: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class TeacherUpdate(BaseModel):
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    employee_id: Optional[str] = None
    position: Optional[str] = None
    designation: Optional[str] = None
    title: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    branch_id: Optional[int] = None
    username: Optional[str] = None  # Updates linked User login username
    hourly_rate: Optional[Decimal] = None

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def validate_hourly_rate_update(cls, v: Any):
        if v is None or v == "":
            return None
        d = Decimal(str(v))
        if d < 0:
            raise ValueError("hourly_rate must be >= 0")
        return d.quantize(Decimal("0.01"))