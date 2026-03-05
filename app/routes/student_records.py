from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.student_records import StudentRecordRequest, StudentRecordResponse, StudentRecordUpdate
from app.apis.student_records import (
    create_student_record, get_student_record, get_student_records,
    update_student_record, delete_student_record
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

student_record = APIRouter()

@student_record.post("/student-records", response_model=StudentRecordResponse, status_code=201)
def create_student_record_endpoint(
    record_data: StudentRecordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """Create a new student record"""
    return create_student_record(db=db, record=record_data, current_user=current_user)

@student_record.get("/student-records/{record_id}", response_model=StudentRecordResponse)
def get_student_record_endpoint(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a student record by ID. Students can only view their own records."""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    # Students can only view their own records
    if current_user.role == UserRole.STUDENT.value:
        # Get the record first
        record = get_student_record(db=db, record_id=record_id, institution_id=institution_id)
        # Find student by user email
        from app.models.student import Student
        student = db.query(Student).filter(
            Student.email == current_user.email,
            Student.institution_id == institution_id,
            Student.deleted_at.is_(None)
        ).first()
        if not student:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student record not found for this user"
            )
        # Verify the record belongs to this student
        if str(record.student_id) != str(student.id):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own records"
            )
        return record
    
    return get_student_record(db=db, record_id=record_id, institution_id=institution_id)

@student_record.get("/student-records", response_model=PaginatedResponse[StudentRecordResponse])
def list_student_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    student_id: Optional[str] = Query(None),
    course_code: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    letter_grade: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of student records with pagination. Students can only view their own records."""
    skip = (page - 1) * page_size
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    # Students can only view their own records
    if current_user.role == UserRole.STUDENT.value:
        # Find student by user email
        from app.models.student import Student
        student = db.query(Student).filter(
            Student.email == current_user.email,
            Student.institution_id == institution_id,
            Student.deleted_at.is_(None)
        ).first()
        if not student:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student record not found for this user"
            )
        # Force student_id filter to their own ID
        student_id = str(student.id)
    
    records, total = get_student_records(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        student_id=student_id,
        course_code=course_code,
        semester=semester,
        letter_grade=letter_grade
    )
    return PaginatedResponse.create(
        items=records,
        total=total,
        page=page,
        page_size=page_size
    )

@student_record.put("/student-records/{record_id}", response_model=StudentRecordResponse)
def update_student_record_endpoint(
    record_id: int,
    record_update: StudentRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """Update a student record"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return update_student_record(
        db=db,
        record_id=record_id,
        record_update=record_update,
        current_user=current_user,
        institution_id=institution_id
    )

@student_record.delete("/student-records/{record_id}", status_code=204)
def delete_student_record_endpoint(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """Delete a student record (soft delete)"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    delete_student_record(db=db, record_id=record_id, current_user=current_user, institution_id=institution_id)
    return None
