"""Academic calendar list, import, and template download."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.tenantDependency import get_db
from app.models.academic_calendar import AcademicCalendar
from app.models.academic_year import AcademicYear
from app.models.role import UserRole
from app.models.user import User
from app.schemas.academic_calendar import (
    AcademicCalendarEntryResponse,
    AcademicCalendarImportErrorItem,
    AcademicCalendarImportResult,
)
from app.services.academic_calendar_import import (
    MAX_FILE_BYTES,
    TEMPLATE_CSV,
    parse_upload_file,
    upsert_calendar_rows,
)

academic_calendar_router = APIRouter()


def _require_institution(current_user: User) -> int:
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="institution_id missing for current user")
    return institution_id


def _get_academic_year_or_404(
    db: Session, institution_id: int, academic_year_id: int
) -> AcademicYear:
    row = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == academic_year_id,
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Academic year not found")
    return row


@academic_calendar_router.get(
    "/academic-calendar",
    response_model=List[AcademicCalendarEntryResponse],
)
def list_academic_calendar(
    academic_year_id: int = Query(..., description="Academic year to list"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    institution_id = _require_institution(current_user)
    _get_academic_year_or_404(db, institution_id, academic_year_id)

    rows = (
        db.query(AcademicCalendar)
        .filter(
            AcademicCalendar.institution_id == institution_id,
            AcademicCalendar.academic_year_id == academic_year_id,
            AcademicCalendar.deleted_at.is_(None),
        )
        .order_by(
            AcademicCalendar.event_date.asc(),
            AcademicCalendar.event_end_date.asc(),
            AcademicCalendar.row_order.asc(),
        )
        .all()
    )
    return [AcademicCalendarEntryResponse.from_model(r) for r in rows]


@academic_calendar_router.post(
    "/academic-calendar/import",
    response_model=AcademicCalendarImportResult,
)
async def import_academic_calendar(
    academic_year_id: int = Query(..., description="Target academic year"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    institution_id = _require_institution(current_user)
    _get_academic_year_or_404(db, institution_id, academic_year_id)

    filename = file.filename or "upload.csv"
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB limit",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    parsed_rows, parse_errors = parse_upload_file(filename, content)
    if not parsed_rows and parse_errors:
        return AcademicCalendarImportResult(
            imported=0,
            updated=0,
            skipped=0,
            errors=[AcademicCalendarImportErrorItem(row=e.row, message=e.message) for e in parse_errors],
            academic_year_id=academic_year_id,
            source_filename=filename,
        )

    imported, updated, skipped = upsert_calendar_rows(
        db,
        institution_id=institution_id,
        academic_year_id=academic_year_id,
        rows=parsed_rows,
        source_filename=filename,
        uploaded_by_user_id=current_user.id,
    )

    return AcademicCalendarImportResult(
        imported=imported,
        updated=updated,
        skipped=skipped,
        errors=[AcademicCalendarImportErrorItem(row=e.row, message=e.message) for e in parse_errors],
        academic_year_id=academic_year_id,
        source_filename=filename,
    )


@academic_calendar_router.get("/academic-calendar/template")
def download_academic_calendar_template(
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    _require_institution(current_user)
    return Response(
        content=TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="academic_calendar_template.csv"'},
    )
