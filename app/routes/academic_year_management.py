import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_any_role, get_current_user_tenant
from app.dependencies.tenantDependency import get_db
from app.models.academic_year import AcademicYear
from app.models.role import UserRole
from app.models.user import User
from app.schemas.academic_year_management import (
    AcademicYearCreateRequest,
    AcademicYearIncrementRequest,
    AcademicYearResponse,
)


academic_year_router = APIRouter()


def _parse_year_name(name: str) -> tuple[int, int]:
    s = (name or "").strip()
    m = re.match(r"^\s*(\d{4})\s*[/\-]\s*(\d{4})\s*$", s)
    if not m:
        raise ValueError("name must be in YYYY/YYYY format")
    a = int(m.group(1))
    b = int(m.group(2))
    if b != a + 1:
        raise ValueError("academic year range must be consecutive (e.g. 2025/2026)")
    return a, b


def _increment_date_str(value: str) -> str:
    s = str(value or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if not m:
        return s
    y, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y + 1:04d}-{mm:02d}-{dd:02d}"


@academic_year_router.get("/academic-years", response_model=list[AcademicYearResponse])
def list_academic_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="institution_id missing for current user")
    rows = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == current_user.institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .order_by(AcademicYear.created_at.desc(), AcademicYear.id.desc())
        .all()
    )
    return rows


@academic_year_router.post(
    "/academic-years",
    response_model=AcademicYearResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_academic_year(
    body: AcademicYearCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)),
):
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="institution_id missing for current user")

    try:
        _parse_year_name(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == institution_id,
            AcademicYear.name == body.name.strip(),
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Academic year already exists")

    if body.is_current:
        (
            db.query(AcademicYear)
            .filter(
                AcademicYear.institution_id == institution_id,
                AcademicYear.deleted_at.is_(None),
            )
            .update({AcademicYear.is_current: False}, synchronize_session=False)
        )

    row = AcademicYear(
        institution_id=institution_id,
        name=body.name.strip(),
        start_date=body.start_date.strip(),
        end_date=body.end_date.strip(),
        is_current=body.is_current,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@academic_year_router.post("/academic-years/{year_id}/set-current", response_model=AcademicYearResponse)
def set_current_academic_year(
    year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)),
):
    institution_id = current_user.institution_id
    row = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == year_id,
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Academic year not found")

    (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .update({AcademicYear.is_current: False}, synchronize_session=False)
    )
    row.is_current = True
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@academic_year_router.post("/academic-years/{year_id}/increment", response_model=AcademicYearResponse)
def increment_academic_year(
    year_id: int,
    body: AcademicYearIncrementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)),
):
    institution_id = current_user.institution_id
    row = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == year_id,
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Academic year not found")

    try:
        a, b = _parse_year_name(row.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot increment year: {exc}")

    new_name = f"{a + 1}/{b + 1}"
    exists = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == institution_id,
            AcademicYear.name == new_name,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail=f"Academic year {new_name} already exists")

    if body.set_current:
        (
            db.query(AcademicYear)
            .filter(
                AcademicYear.institution_id == institution_id,
                AcademicYear.deleted_at.is_(None),
            )
            .update({AcademicYear.is_current: False}, synchronize_session=False)
        )

    new_row = AcademicYear(
        institution_id=institution_id,
        name=new_name,
        start_date=_increment_date_str(row.start_date) if body.copy_date_span else row.start_date,
        end_date=_increment_date_str(row.end_date) if body.copy_date_span else row.end_date,
        is_current=body.set_current,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row
