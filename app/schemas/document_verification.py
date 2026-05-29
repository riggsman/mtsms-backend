"""Schemas for public academic document verification."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerifiedDocumentCourseItem(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    semester: Optional[str] = None
    type: Optional[str] = None
    credit_value: Optional[float] = None
    grade: Optional[str] = None
    ca_mark: Optional[float] = None
    exam_mark: Optional[float] = None
    total_mark: Optional[float] = None
    points: Optional[float] = None
    remark: Optional[str] = None
    credits_earned: Optional[float] = None


class VerifiedDocumentStudent(BaseModel):
    student_no: str
    surname: Optional[str] = None
    other_names: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    faculty: Optional[str] = None
    degree_proposed: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    date_of_enrolment: Optional[str] = None


class VerifiedDocumentSummary(BaseModel):
    semester_gpa: Optional[float] = None
    cumulative_gpa: Optional[float] = None
    total_credits: Optional[float] = None
    total_credits_earned: Optional[float] = None
    total_ca: Optional[float] = None
    total_exam: Optional[float] = None
    grand_total: Optional[float] = None


class DocumentPublicVerificationResponse(BaseModel):
    verified: bool = True
    document_type: str = Field(..., description="transcript or result_slip")
    document_title: str
    institution_name: Optional[str] = None
    issued_at: datetime
    date_printed: Optional[str] = None
    semester: Optional[str] = None
    student: VerifiedDocumentStudent
    courses: List[VerifiedDocumentCourseItem] = Field(default_factory=list)
    summary: Optional[VerifiedDocumentSummary] = None
    verification_message: str = "This document is authentic and was issued by the institution."
