from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.department import Department
from app.models.student import Student
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse, EnrollmentWithCourse
from app.exceptions import NotFoundError, ConflictError

def create_enrollment(db: Session, enrollment: EnrollmentCreate):
    """Create a new enrollment"""
    # Check if enrollment already exists
    existing = db.query(Enrollment).filter(
        and_(
            Enrollment.student_id == enrollment.student_id,
            Enrollment.course_id == enrollment.course_id,
            Enrollment.deleted_at.is_(None)
        )
    ).first()
    
    if existing:
        raise ConflictError("Student is already enrolled in this course")
    
    # Verify student exists
    student = db.query(Student).filter(Student.id == enrollment.student_id).first()
    if not student:
        raise NotFoundError(f"Student with ID {enrollment.student_id} not found")
    
    # Verify course exists
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    if not course:
        raise NotFoundError(f"Course with ID {enrollment.course_id} not found")
    
    db_enrollment = Enrollment(
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        status=enrollment.status or "active"
    )
    
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)
    
    return db_enrollment

def get_enrollment(db: Session, enrollment_id: int):
    """Get enrollment by ID"""
    enrollment = db.query(Enrollment).filter(
        and_(
            Enrollment.id == enrollment_id,
            Enrollment.deleted_at.is_(None)
        )
    ).first()
    
    if not enrollment:
        raise NotFoundError(f"Enrollment with ID {enrollment_id} not found")
    
    return enrollment

def get_student_enrollments(db: Session, student_id: int, include_course_info: bool = True):
    """Get all enrollments for a student"""
    enrollments = db.query(Enrollment).filter(
        and_(
            Enrollment.student_id == student_id,
            Enrollment.deleted_at.is_(None)
        )
    ).all()
    
    if include_course_info:
        result = []
        for enrollment in enrollments:
            course = db.query(Course).filter(Course.id == enrollment.course_id).first()
            department = None
            if course:
                department = db.query(Department).filter(Department.id == course.department_id).first()
            
            enrollment_dict = {
                "id": enrollment.id,
                "student_id": enrollment.student_id,
                "course_id": enrollment.course_id,
                "status": enrollment.status,
                "enrollment_date": enrollment.enrollment_date,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
                "course_code": course.code if course else None,
                "course_name": course.name if course else None,
                "department_name": department.name if department else None,
                "department_id": course.department_id if course else None
            }
            result.append(enrollment_dict)
        return result
    
    return enrollments

def get_course_enrollments(db: Session, course_id: int):
    """Get all enrollments for a course"""
    enrollments = db.query(Enrollment).filter(
        and_(
            Enrollment.course_id == course_id,
            Enrollment.deleted_at.is_(None)
        )
    ).all()
    
    return enrollments

def update_enrollment(db: Session, enrollment_id: int, enrollment_update: EnrollmentUpdate):
    """Update an enrollment"""
    enrollment = db.query(Enrollment).filter(
        and_(
            Enrollment.id == enrollment_id,
            Enrollment.deleted_at.is_(None)
        )
    ).first()
    
    if not enrollment:
        raise NotFoundError(f"Enrollment with ID {enrollment_id} not found")
    
    if enrollment_update.status is not None:
        enrollment.status = enrollment_update.status
    
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

def delete_enrollment(db: Session, enrollment_id: int):
    """Soft delete an enrollment"""
    enrollment = db.query(Enrollment).filter(
        and_(
            Enrollment.id == enrollment_id,
            Enrollment.deleted_at.is_(None)
        )
    ).first()
    
    if not enrollment:
        raise NotFoundError(f"Enrollment with ID {enrollment_id} not found")
    
    from datetime import datetime
    enrollment.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Enrollment deleted successfully"}
