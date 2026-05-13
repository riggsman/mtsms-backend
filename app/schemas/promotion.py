from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StudentYearOutcomeUpsertRequest(BaseModel):
    student_id: int
    academic_year_id: int
    final_status: str = Field(..., min_length=3, max_length=30)
    term: Optional[str] = Field(default="term3", max_length=20)
    notes: Optional[str] = None


class PromotionCandidateItem(BaseModel):
    student_id: int
    student_name: str
    from_class_id: int
    from_class_name: Optional[str] = None
    to_class_id: Optional[int] = None
    to_class_name: Optional[str] = None
    reason: Optional[str] = None


class PromotionPreviewRequest(BaseModel):
    academic_year_id: int
    final_status: str = Field(default="promoted", min_length=3, max_length=30)
    student_ids: Optional[List[int]] = None


class PromotionPreviewResponse(BaseModel):
    eligible_count: int
    mapped_count: int
    unresolved_count: int
    items: List[PromotionCandidateItem]


class PromotionExecuteRequest(BaseModel):
    academic_year_id: int
    final_status: str = Field(default="promoted", min_length=3, max_length=30)
    student_ids: Optional[List[int]] = None


class PromotionExecuteResponse(BaseModel):
    execution_id: str
    moved: int
    archived: int
    skipped: int
    errors: List[str]


class StudentYearOutcomeResponse(BaseModel):
    id: int
    student_id: int
    institution_id: int
    academic_year_id: int
    term: Optional[str] = None
    final_status: str
    notes: Optional[str] = None
    decided_by: Optional[int] = None
    decided_at: datetime

    class Config:
        from_attributes = True
