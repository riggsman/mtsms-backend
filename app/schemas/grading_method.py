from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class GradingRangeRequest(BaseModel):
    minimum_score: float = Field(..., ge=0, le=100)
    maximum_score: float = Field(..., ge=0, le=100)
    grade: str = Field(..., min_length=1, max_length=10)
    grade_point: float = Field(..., ge=0, le=4)


class GradingRangeResponse(BaseModel):
    id: int
    minimum_score: float
    maximum_score: float
    grade: str
    grade_point: float

    class Config:
        from_attributes = True


class GradingMethodResponse(BaseModel):
    id: int
    name: str
    institution_id: Optional[int] = None
    is_system_default: bool
    created_at: datetime
    grading_ranges: List[GradingRangeResponse] = []

    class Config:
        from_attributes = True


class GradingMethodUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    grading_ranges: List[GradingRangeRequest] = Field(..., min_length=1)
