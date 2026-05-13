from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, constr


class PayrollTimeEntryResponse(BaseModel):
    id: int
    institution_id: int
    teacher_id: int
    course_id: Optional[int] = None
    course_code_snapshot: Optional[str] = None
    clock_in_code_plain: Optional[str] = None
    clock_out_code_plain: Optional[str] = None
    clock_in_at: datetime
    clock_out_at: Optional[datetime] = None
    lecturer_clock_out_confirmed_at: Optional[datetime] = None
    student_clock_out_confirmed_at: Optional[datetime] = None
    student_confirmer_id: Optional[int] = None
    clock_out_finalized_at: Optional[datetime] = None
    duration_hours: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayrollClockStatusResponse(BaseModel):
    """Whether the current user has an open payroll session."""
    is_clocked_in: bool
    open_entry_id: Optional[int] = None
    clock_in_at: Optional[datetime] = None
    course_code_snapshot: Optional[str] = None
    awaiting_student_confirmation: bool = False
    # Plaintext codes while the session is active (cleared after successful clock-in / clock-out confirm).
    clock_in_code_plain: Optional[str] = None
    clock_out_code_plain: Optional[str] = None


class PayrollCodeGenerateRequest(BaseModel):
    teacher_id: int
    course_code: str
    # UI sends 240 by default; must match payrollAPI.generateCodes in the frontend.
    expires_in_minutes: Optional[int] = Field(default=30, ge=1, le=24 * 60)


class PayrollCodeGenerateResponse(BaseModel):
    entry_id: int
    teacher_id: int
    course_id: int
    course_code: str
    clock_in_code: str
    clock_out_code: str
    expires_at: Optional[datetime] = None


class PayrollClockInRequest(BaseModel):
    course_code: str
    clock_in_code: constr(min_length=5, max_length=5)


class PayrollClockOutConfirmRequest(BaseModel):
    course_code: str
    clock_out_code: constr(min_length=5, max_length=5)


class PayrollReportRow(BaseModel):
    teacher_id: int
    firstname: str
    lastname: str
    employee_id: str
    hourly_rate: Optional[Decimal] = None
    total_hours: Decimal = Field(default=Decimal("0"))
    gross_pay: Optional[Decimal] = None


class PayrollReportResponse(BaseModel):
    from_date: str
    to_date: str
    rows: List[PayrollReportRow]


class PayrollCodeAuditRow(BaseModel):
    """One payroll session row for code issuance / consumption traceability."""

    entry_id: int
    teacher_id: int
    teacher_name: str
    course_code: Optional[str] = None
    codes_generated_at: datetime
    codes_expires_at: Optional[datetime] = None
    generated_by_user_id: Optional[int] = None
    generated_by_name: Optional[str] = None
    clock_in_code_plain: Optional[str] = None
    clock_out_code_plain: Optional[str] = None
    clock_in_code_used: bool
    clock_out_code_used: bool
    clock_in_code_used_at: Optional[datetime] = None
    clock_out_code_used_at: Optional[datetime] = None
