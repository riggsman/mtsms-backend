from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse, EnrollmentWithCourse
from app.apis.enrollments import (
    create_enrollment, get_enrollment, get_student_enrollments,
    get_course_enrollments, update_enrollment, delete_enrollment
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

enrollment = APIRouter()

@enrollment.post("/enrollments", response_model=EnrollmentResponse, status_code=201)
def create_enrollment_endpoint(
    enrollment_data: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Enroll a student in a course. Students can enroll themselves."""
    # Allow students to enroll themselves, or admin/staff to enroll any student
    if current_user.role == UserRole.STUDENT.value:
        # Find student by user email
        from app.models.student import Student
        student = db.query(Student).filter(Student.email == current_user.email).first()
        if not student:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student record not found for this user"
            )
        # Students can only enroll themselves
        if enrollment_data.student_id != student.id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only enroll themselves"
            )
    
    return create_enrollment(db=db, enrollment=enrollment_data, current_user=current_user)

@enrollment.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment_endpoint(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get enrollment by ID"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return get_enrollment(db=db, enrollment_id=enrollment_id, institution_id=institution_id)

@enrollment.get("/enrollments/student/{student_id}", response_model=list[EnrollmentWithCourse])
def get_student_enrollments_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all enrollments for a student"""
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    
    # Students can only view their own enrollments
    if current_user.role == UserRole.STUDENT.value:
        # Find student by user email (tenant-scoped)
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
        if student.id != student_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own enrollments"
            )
    
    return get_student_enrollments(db=db, student_id=student_id, include_course_info=True, institution_id=institution_id)

@enrollment.get("/enrollments/course/{course_id}")
def get_course_enrollments_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.TEACHER))
):
    """Get all enrollments for a course with student information (admin/staff/teacher only)"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return get_course_enrollments(db=db, course_id=course_id, institution_id=institution_id)

@enrollment.put("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment_endpoint(
    enrollment_id: int,
    enrollment_update: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF))
):
    """Update an enrollment (admin/staff only)"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return update_enrollment(db=db, enrollment_id=enrollment_id, enrollment_update=enrollment_update, institution_id=institution_id)

@enrollment.delete("/enrollments/{enrollment_id}")
def delete_enrollment_endpoint(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Delete (unenroll) a student from a course"""
    # Students can unenroll themselves
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    enrollment = get_enrollment(db, enrollment_id, institution_id=institution_id)
    if current_user.role == UserRole.STUDENT.value:
        # Get student ID from user email
        from app.models.student import Student
        student = db.query(Student).filter(Student.email == current_user.email).first()
        if not student:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student record not found for this user"
            )
        if student.id != enrollment.student_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only unenroll themselves"
            )
    
    return delete_enrollment(db=db, enrollment_id=enrollment_id, institution_id=institution_id)
