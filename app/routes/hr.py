from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from app.schemas.hr import (
    StaffDocumentCreate, StaffDocumentResponse,
    StaffAttendanceCreate, StaffAttendanceResponse
)
from app.apis.hr import (
    create_staff_document, get_staff_documents,
    mark_staff_attendance, get_staff_attendance
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from datetime import datetime

hr_router = APIRouter()

# Staff Documents
@hr_router.post("/hr/documents", response_model=StaffDocumentResponse, status_code=201)
def upload_staff_document(
    doc_data: StaffDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    return create_staff_document(db=db, doc_data=doc_data, institution_id=current_user.institution_id)

@hr_router.get("/hr/documents", response_model=List[StaffDocumentResponse])
def list_staff_documents(
    staff_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    return get_staff_documents(db=db, institution_id=current_user.institution_id, staff_id=staff_id)

# Staff Attendance
@hr_router.post("/hr/attendance", response_model=StaffAttendanceResponse)
def record_staff_attendance(
    attendance_data: StaffAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    return mark_staff_attendance(db=db, attendance_data=attendance_data, institution_id=current_user.institution_id)

@hr_router.get("/hr/attendance", response_model=List[StaffAttendanceResponse])
def list_staff_attendance(
    staff_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    return get_staff_attendance(db=db, institution_id=current_user.institution_id, staff_id=staff_id, start_date=start_date, end_date=end_date)
