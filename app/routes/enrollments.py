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
    
    return create_enrollment(db=db, enrollment=enrollment_data)

@enrollment.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment_endpoint(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get enrollment by ID"""
    return get_enrollment(db=db, enrollment_id=enrollment_id)

@enrollment.get("/enrollments/student/{student_id}", response_model=list[EnrollmentWithCourse])
def get_student_enrollments_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all enrollments for a student"""
    # Students can only view their own enrollments
    if current_user.role == UserRole.STUDENT.value:
        # Find student by user email
        from app.models.student import Student
        student = db.query(Student).filter(Student.email == current_user.email).first()
        if not student or student.id != student_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own enrollments"
            )
    
    return get_student_enrollments(db=db, student_id=student_id, include_course_info=True)

@enrollment.get("/enrollments/course/{course_id}", response_model=list[EnrollmentResponse])
def get_course_enrollments_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.TEACHER))
):
    """Get all enrollments for a course (admin/staff/teacher only)"""
    return get_course_enrollments(db=db, course_id=course_id)

@enrollment.put("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment_endpoint(
    enrollment_id: int,
    enrollment_update: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF))
):
    """Update an enrollment (admin/staff only)"""
    return update_enrollment(db=db, enrollment_id=enrollment_id, enrollment_update=enrollment_update)

@enrollment.delete("/enrollments/{enrollment_id}")
def delete_enrollment_endpoint(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Delete (unenroll) a student from a course"""
    # Students can unenroll themselves
    enrollment = get_enrollment(db, enrollment_id)
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
    
    return delete_enrollment(db=db, enrollment_id=enrollment_id)
