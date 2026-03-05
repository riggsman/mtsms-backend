from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.department import Department
from app.models.student import Student
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse, EnrollmentWithCourse
from app.exceptions import NotFoundError, ConflictError, ValidationError

def create_enrollment(db: Session, enrollment: EnrollmentCreate, current_user: User | None = None):
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
    student = db.query(Student).filter(
        Student.id == enrollment.student_id,
        Student.deleted_at.is_(None),
    ).first()
    if not student:
        raise NotFoundError(f"Student with ID {enrollment.student_id} not found")
    
    # Verify course exists
    course = db.query(Course).filter(
        Course.id == enrollment.course_id,
        Course.deleted_at.is_(None),
    ).first()
    if not course:
        raise NotFoundError(f"Course with ID {enrollment.course_id} not found")

    # Determine institution_id and enforce tenant isolation
    institution_id = course.institution_id or student.institution_id
    if not institution_id:
        raise ValidationError("institution_id could not be determined for this enrollment")

    # Cross-check student vs course tenant
    if student.institution_id != course.institution_id:
        raise ValidationError("Student and course belong to different institutions")

    # If we have a current_user with institution_id, enforce it (unless system role)
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        if current_user.institution_id and current_user.institution_id != institution_id:
            raise ValidationError("Cross-tenant enrollment is not allowed")
    
    db_enrollment = Enrollment(
        institution_id=institution_id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        status=enrollment.status or "active"
    )
    
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)
    
    return db_enrollment

def get_enrollment(db: Session, enrollment_id: int, institution_id: int | None = None):
    """Get enrollment by ID"""
    query = db.query(Enrollment).filter(
        and_(
            Enrollment.id == enrollment_id,
            Enrollment.deleted_at.is_(None)
        )
    )
    if institution_id is not None:
        query = query.filter(Enrollment.institution_id == institution_id)
    enrollment = query.first()
    
    if not enrollment:
        raise NotFoundError(f"Enrollment with ID {enrollment_id} not found")
    
    return enrollment

def get_student_enrollments(db: Session, student_id: int, include_course_info: bool = True, institution_id: int | None = None):
    """Get all enrollments for a student"""
    query = db.query(Enrollment).filter(
        and_(
            Enrollment.student_id == student_id,
            Enrollment.deleted_at.is_(None)
        )
    )
    if institution_id is not None:
        query = query.filter(Enrollment.institution_id == institution_id)
    enrollments = query.all()
    
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

def get_course_enrollments(db: Session, course_id: int, institution_id: int | None = None):
    """Get all enrollments for a course with student information"""
    query = db.query(Enrollment).filter(
        and_(
            Enrollment.course_id == course_id,
            Enrollment.deleted_at.is_(None)
        )
    )
    if institution_id is not None:
        query = query.filter(Enrollment.institution_id == institution_id)
    enrollments = query.all()
    
    # Enrich with student information
    result = []
    for enrollment in enrollments:
        student = db.query(Student).filter(
            Student.id == enrollment.student_id,
            Student.deleted_at.is_(None)
        ).first()
        
        enrollment_dict = {
            "id": enrollment.id,
            "student_id": enrollment.student_id,
            "course_id": enrollment.course_id,
            "status": enrollment.status,
            "created_at": enrollment.created_at,
            "enrollment_date": enrollment.enrollment_date,
            "student": {
                "id": student.id if student else None,
                "student_id": student.student_id if student else None,
                "firstname": student.firstname if student else None,
                "lastname": student.lastname if student else None,
                "name": f"{student.firstname} {student.lastname}".strip() if student and student.firstname and student.lastname else None,
                "email": student.email if student else None
            } if student else None
        }
        result.append(enrollment_dict)
    
    return result

def update_enrollment(db: Session, enrollment_id: int, enrollment_update: EnrollmentUpdate, institution_id: int | None = None):
    """Update an enrollment"""
    query = db.query(Enrollment).filter(
        and_(
            Enrollment.id == enrollment_id,
            Enrollment.deleted_at.is_(None)
        )
    )
    if institution_id is not None:
        query = query.filter(Enrollment.institution_id == institution_id)
    enrollment = query.first()
    
    if not enrollment:
        raise NotFoundError(f"Enrollment with ID {enrollment_id} not found")
    
    if enrollment_update.status is not None:
        enrollment.status = enrollment_update.status
    
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

def delete_enrollment(db: Session, enrollment_id: int, institution_id: int | None = None):
    """Soft delete an enrollment"""
    query = db.query(Enrollment).filter(
        and_(
            Enrollment.id == enrollment_id,
            Enrollment.deleted_at.is_(None)
        )
    )
    if institution_id is not None:
        query = query.filter(Enrollment.institution_id == institution_id)
    enrollment = query.first()
    
    if not enrollment:
        raise NotFoundError(f"Enrollment with ID {enrollment_id} not found")
    
    from datetime import datetime
    enrollment.deleted_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Enrollment deleted successfully"}
