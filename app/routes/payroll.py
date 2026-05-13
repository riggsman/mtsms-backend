from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.apis import payroll as payroll_api
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.helpers.pagination import PaginatedResponse
from app.models.role import UserRole
from app.models.user import User
from app.schemas.payroll import (
    PayrollClockInRequest,
    PayrollClockStatusResponse,
    PayrollClockOutConfirmRequest,
    PayrollCodeAuditRow,
    PayrollCodeGenerateRequest,
    PayrollCodeGenerateResponse,
    PayrollReportResponse,
    PayrollReportRow,
    PayrollTimeEntryResponse,
)

router = APIRouter()


@router.get("/payroll/me/status", response_model=PayrollClockStatusResponse)
def payroll_me_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.TEACHER)),
):
    is_in, eid, at, course_code, waiting_student, cin_plain, cout_plain = payroll_api.get_clock_status(
        db, current_user
    )
    return PayrollClockStatusResponse(
        is_clocked_in=is_in,
        open_entry_id=eid,
        clock_in_at=at,
        course_code_snapshot=course_code,
        awaiting_student_confirmation=waiting_student,
        clock_in_code_plain=cin_plain,
        clock_out_code_plain=cout_plain,
    )


@router.post("/payroll/codes/generate", response_model=PayrollCodeGenerateResponse)
def payroll_generate_codes(
    payload: PayrollCodeGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
            UserRole.SECRETARY,
            UserRole.SYSTEM_ADMIN,
            UserRole.SYSTEM_SUPER_ADMIN,
        )
    ),
):
    ttl = payload.expires_in_minutes
    if ttl is None:
        ttl = payroll_api.CODE_TTL_MINUTES
    return PayrollCodeGenerateResponse(
        **payroll_api.generate_codes(
            db,
            current_user,
            teacher_id=payload.teacher_id,
            course_code=payload.course_code,
            expires_in_minutes=ttl,
        )
    )


@router.post("/payroll/clock-in", response_model=PayrollTimeEntryResponse)
def payroll_clock_in(
    payload: PayrollClockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.TEACHER)),
):
    entry = payroll_api.clock_in_with_code(
        db, current_user, course_code=payload.course_code, clock_in_code=payload.clock_in_code
    )
    return PayrollTimeEntryResponse.model_validate(entry)


@router.post("/payroll/clock-out/lecturer", response_model=PayrollTimeEntryResponse)
def payroll_clock_out_lecturer(
    payload: PayrollClockOutConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.TEACHER)),
):
    entry = payroll_api.lecturer_clock_out_confirm(
        db, current_user, course_code=payload.course_code, clock_out_code=payload.clock_out_code
    )
    return PayrollTimeEntryResponse.model_validate(entry)


@router.post("/payroll/clock-out/student", response_model=PayrollTimeEntryResponse)
def payroll_clock_out_student(
    payload: PayrollClockOutConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STUDENT)),
):
    entry = payroll_api.student_clock_out_confirm(
        db, current_user, course_code=payload.course_code, clock_out_code=payload.clock_out_code
    )
    return PayrollTimeEntryResponse.model_validate(entry)


@router.get("/payroll/me/entries", response_model=PaginatedResponse[PayrollTimeEntryResponse])
def payroll_my_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.TEACHER)),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = payroll_api.list_my_entries(
        db, current_user, from_date=from_date, to_date=to_date, page=page, page_size=page_size
    )
    return PaginatedResponse.create(
        items=[PayrollTimeEntryResponse.model_validate(x) for x in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/payroll/report", response_model=PayrollReportResponse)
def payroll_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    teacher_id: Optional[int] = Query(None),
):
    rows = payroll_api.payroll_report(db, current_user, from_date, to_date, teacher_id=teacher_id)
    return PayrollReportResponse(
        from_date=from_date,
        to_date=to_date,
        rows=[PayrollReportRow(**r) for r in rows],
    )


@router.get("/payroll/codes/audit", response_model=PaginatedResponse[PayrollCodeAuditRow])
def payroll_codes_audit(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
    from_date: str = Query(..., description="YYYY-MM-DD — filter by codes sent time"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    teacher_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = payroll_api.list_payroll_codes_audit(
        db,
        current_user,
        from_date,
        to_date,
        teacher_id=teacher_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(
        items=[PayrollCodeAuditRow(**x) for x in items],
        total=total,
        page=page,
        page_size=page_size,
    )
