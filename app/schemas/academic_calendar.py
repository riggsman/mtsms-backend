"""Schemas for academic calendar entries and import results."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.academic_calendar_import import format_date_range_display


class AcademicCalendarEntryResponse(BaseModel):
    id: int
    institution_id: int
    academic_year_id: int
    event_date: date
    event_end_date: date
    event_date_formatted: Optional[str] = None
    activity: str
    row_order: int
    source_filename: Optional[str] = None
    uploaded_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, row) -> "AcademicCalendarEntryResponse":
        start = row.event_date
        end = getattr(row, "event_end_date", None) or start
        return cls(
            id=row.id,
            institution_id=row.institution_id,
            academic_year_id=row.academic_year_id,
            event_date=start,
            event_end_date=end,
            event_date_formatted=format_date_range_display(start, end) if start else None,
            activity=row.activity,
            row_order=row.row_order or 0,
            source_filename=row.source_filename,
            uploaded_by_user_id=row.uploaded_by_user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class AcademicCalendarImportErrorItem(BaseModel):
    row: int
    message: str


class AcademicCalendarImportResult(BaseModel):
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[AcademicCalendarImportErrorItem] = Field(default_factory=list)
    academic_year_id: int
    source_filename: Optional[str] = None
