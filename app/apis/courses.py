from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.models.course import Course
from app.models.department import Department
from app.models.user import User
from app.schemas.courses import CourseRequest, CourseResponse, CourseUpdate
from app.exceptions import NotFoundError, ConflictError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity

def create_course(db: Session, course: CourseRequest, institution_id: Optional[int] = None, current_user: Optional[User] = None) -> Course:
    """Create a new course"""
    # Use institution_id from request if provided, otherwise use the parameter
    final_institution_id = course.institution_id or institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or pass it as a parameter")
    
    # Check if course code already exists for this institution
    existing = db.query(Course).filter(
        Course.code == course.code,
        Course.institution_id == final_institution_id,
        Course.deleted_at.is_(None)
    ).first()
    if existing:
        raise ConflictError(f"Course with code {course.code} already exists for this institution")
    
    # Create course with institution_id
    course_dict = course.dict()
    course_dict['institution_id'] = final_institution_id
    new_course = Course(**course_dict)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    
    # Add department_name to the new course
    if new_course.department_id:
        department = db.query(Department).filter(
            Department.id == new_course.department_id,
            Department.deleted_at.is_(None)
        ).first()
        if department:
            new_course.department_name = department.name
        else:
            new_course.department_name = None
    else:
        new_course.department_name = None
    
    # Log activity if current_user is provided
    if current_user:
        try:
            course_name = f"{course.code} - {course.name}"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="course",
                entity_id=new_course.id,
                entity_name=course_name,
                institution_id=final_institution_id,
                content=f"Created course: {course_name}"
            )
        except Exception as e:
            print(f"Error logging course creation activity: {e}")
    
    return new_course


def get_course(db: Session, course_id: int, institution_id: Optional[int] = None) -> Course:
    """Get a course by ID"""
    query = db.query(Course).filter(
        Course.id == course_id,
        Course.deleted_at.is_(None)
    )
    if institution_id is not None:
        query = query.filter(Course.institution_id == institution_id)
    course = query.first()
    if not course:
        raise NotFoundError(f"Course with ID {course_id} not found")
    
    # Add department_name to the course object
    if course.department_id:
        department = db.query(Department).filter(
            Department.id == course.department_id,
            Department.deleted_at.is_(None)
        ).first()
        if department:
            course.department_name = department.name
        else:
            course.department_name = None
    else:
        course.department_name = None
    
    return course


def get_courses(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None,
    department_id: Optional[int] = None,
    level_id: Optional[int] = None
) -> tuple[List[Course], int]:
    """Get list of courses with pagination"""
    query = db.query(Course).filter(Course.deleted_at.is_(None))
    
    # Filter by institution_id if provided (required for multi-tenancy)
    # If institution_id is None, this might be a system admin viewing all courses
    # For tenant users, institution_id should always be provided
    if institution_id is not None:
        query = query.filter(Course.institution_id == institution_id)
    
    if department_id:
        query = query.filter(Course.department_id == department_id)
    
    if level_id:
        query = query.filter(Course.level_id == level_id)
    
    courses, total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    
    # Add department_name to each course
    department_ids = [course.department_id for course in courses if course.department_id]
    if department_ids:
        departments = db.query(Department).filter(
            Department.id.in_(department_ids),
            Department.deleted_at.is_(None)
        ).all()
        department_map = {dept.id: dept.name for dept in departments}
        
        for course in courses:
            if course.department_id:
                course.department_name = department_map.get(course.department_id)
            else:
                course.department_name = None
    else:
        for course in courses:
            course.department_name = None
    
    return courses, total


def update_course(
    db: Session,
    course_id: int,
    course_update: CourseUpdate,
    current_user: Optional[User] = None,
    institution_id: Optional[int] = None
) -> Course:
    """Update a course"""
    course = get_course(db, course_id, institution_id=institution_id)
    
    update_data = course_update.dict(exclude_unset=True)
    
    # Check code uniqueness if being updated
    if "code" in update_data:
        existing = db.query(Course).filter(
            Course.code == update_data["code"],
            Course.id != course_id
        ).first()
        if existing:
            raise ConflictError(f"Course with code {update_data['code']} already exists")
    
    for field, value in update_data.items():
        setattr(course, field, value)
    
    db.commit()
    db.refresh(course)
    
    # Add department_name to the updated course
    if course.department_id:
        department = db.query(Department).filter(
            Department.id == course.department_id,
            Department.deleted_at.is_(None)
        ).first()
        if department:
            course.department_name = department.name
        else:
            course.department_name = None
    else:
        course.department_name = None
    
    # Log activity if current_user is provided
    if current_user:
        try:
            course_name = f"{course.code} - {course.name}"
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="course",
                entity_id=course.id,
                entity_name=course_name,
                institution_id=course.institution_id,
                content=f"Updated course: {course_name}"
            )
        except Exception as e:
            print(f"Error logging course update activity: {e}")
    
    return course


def delete_course(db: Session, course_id: int, current_user: Optional[User] = None, institution_id: Optional[int] = None) -> bool:
    """Soft delete a course"""
    course = get_course(db, course_id, institution_id=institution_id)
    course_name = f"{course.code} - {course.name}"
    institution_id = course.institution_id
    from datetime import datetime
    course.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="course",
                entity_id=course_id,
                entity_name=course_name,
                institution_id=institution_id,
                content=f"Deleted course: {course_name}"
            )
        except Exception as e:
            print(f"Error logging course deletion activity: {e}")
    
    return True


def get_course_by_code(db: Session, code: str) -> Optional[Course]:
    """Get course by code"""
    return db.query(Course).filter(
        Course.code == code,
        Course.deleted_at.is_(None)
    ).first()
