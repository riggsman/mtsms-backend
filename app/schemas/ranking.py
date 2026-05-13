from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class StudentTopRankItem(BaseModel):
    student_id: str
    name: str
    score: float
    rank: int


class ClassTopRankItem(BaseModel):
    class_id: int
    name: str
    score: float
    rank: int


class SchoolTopRankItem(BaseModel):
    school_id: int
    name: str
    score: float
    rank: int


class CourseRankItem(BaseModel):
    course_code: str
    score: float
    rank: int
    academic_year: Optional[str] = None
    semester_or_term: Optional[str] = None
    computed_at: Optional[str] = None


class CurrentStudentRanking(BaseModel):
    student_id: str
    course_ranks: List[CourseRankItem]
    class_rank: Optional[int] = None
    school_rank: Optional[int] = None


class RankingsPayload(BaseModel):
    students: dict
    classes: dict
    schools: dict
    course: List[CourseRankItem]
    current_student: Optional[CurrentStudentRanking] = None


class RankingsMeta(BaseModel):
    tenant_category: Optional[str] = None
    scope: str = "institution"
    top_n: int = 3
    computed_at: datetime


class RankingsResponse(BaseModel):
    rankings: RankingsPayload
    meta: RankingsMeta


class RankingRecomputeRequest(BaseModel):
    course_code: str
    academic_year: str
    semester_or_term: str


class RankingRecomputeResponse(BaseModel):
    status: str
    correlation_id: str
