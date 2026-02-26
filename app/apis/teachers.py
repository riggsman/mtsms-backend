from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.teachers import TeacherRequest, TeacherResponse, TeacherUpdate
from app.exceptions import NotFoundError, ConflictError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity, get_user_display_name
from app.services.email_service import EmailService
from app.helpers.async_helper import run_async_safe

def create_teacher(db: Session, teacher: TeacherRequest, current_user: Optional[User] = None) -> Teacher:
    """Create a new teacher and automatically create a user account with staff role"""
    from app.models.user import User
    from app.authentication.authenticator import hash_password
    
    # Determine institution_id
    institution_id = teacher.institution_id
    if not institution_id and current_user:
        institution_id = current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    # Check if email already exists in teachers table
    existing_teacher = db.query(Teacher).filter(Teacher.email == teacher.email).first()
    if existing_teacher:
        raise ConflictError(f"Teacher with email {teacher.email} already exists")
    
    # Check if employee_id already exists
    existing_teacher = db.query(Teacher).filter(Teacher.employee_id == teacher.employee_id).first()
    if existing_teacher:
        raise ConflictError(f"Teacher with employee_id {teacher.employee_id} already exists")
    
    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == teacher.email).first()
    if existing_user:
        raise ConflictError(f"User with email {teacher.email} already exists. Please use a different email.")
    
    # Create teacher record
    teacher_dict = teacher.dict(exclude={'institution_id'})
    teacher_dict['institution_id'] = institution_id
    new_teacher = Teacher(**teacher_dict)
    db.add(new_teacher)
    db.flush()  # Flush to get the teacher ID
    
    # Generate a default password (employee_id or email prefix)
    default_password = teacher.employee_id or teacher.email.split('@')[0]
    hashed_password = hash_password(default_password)
    
    # Generate username from email
    username = teacher.email.split('@')[0]
    
    # Create user account with staff role
    new_user = User(
        institution_id=institution_id,
        firstname=teacher.firstname,
        lastname=teacher.lastname,
        middlename=teacher.middlename or '',
        gender=teacher.gender or 'Male',  # Default to 'Male' if not provided
        address=teacher.address or '',  # Default to empty string if not provided
        email=teacher.email,
        phone=teacher.phone or '',
        username=username,
        password=hashed_password,
        role='staff',  # Automatically set to staff role
        user_type='TENANT',  # Teachers are always TENANT users
        is_active='active',
        must_change_password='true'  # Force password change on first login
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_teacher)
    db.refresh(new_user)
    
    # Send registration email asynchronously (non-blocking)
    lecturer_name = f"{teacher.firstname} {teacher.lastname}"
    run_async_safe(
        EmailService.send_lecturer_registration_email(
            lecturer_name=lecturer_name,
            lecturer_email=teacher.email,
            username=username,
            password=default_password,  # Send plain password for first login
            employee_id=teacher.employee_id,
            institution_name=None  # Can be enhanced to fetch institution name if needed
        )
    )
    
    # Log activity if current_user is provided
    if current_user and institution_id:
        try:
            teacher_name = f"{teacher.firstname} {teacher.lastname} ({teacher.employee_id})"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="teacher",
                entity_id=new_teacher.id,
                entity_name=teacher_name,
                institution_id=institution_id,
                content=f"Created staff/teacher: {teacher_name} with staff user account (Employee ID: {teacher.employee_id})"
            )
        except Exception as e:
            print(f"Error logging teacher creation activity: {e}")
    
    return new_teacher


def get_teacher(db: Session, teacher_id: int) -> Teacher:
    """Get a teacher by ID"""
    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id,
        Teacher.deleted_at.is_(None)
    ).first()
    if not teacher:
        raise NotFoundError(f"Teacher with ID {teacher_id} not found")
    return teacher


def get_teachers(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None,
    department_id: Optional[int] = None
) -> tuple[List[Teacher], int]:
    """Get list of teachers with pagination"""
    query = db.query(Teacher).filter(Teacher.deleted_at.is_(None))
    
    if institution_id is not None:
        query = query.filter(Teacher.institution_id == institution_id)
    
    if department_id:
        query = query.filter(Teacher.department_id == department_id)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def update_teacher(db: Session, teacher_id: int, teacher_update: TeacherUpdate, current_user: Optional[User] = None) -> Teacher:
    """Update a teacher"""
    teacher = get_teacher(db, teacher_id)
    
    update_data = teacher_update.dict(exclude_unset=True)
    
    # Check email uniqueness if being updated
    if "email" in update_data:
        existing = db.query(Teacher).filter(
            Teacher.email == update_data["email"],
            Teacher.id != teacher_id
        ).first()
        if existing:
            raise ConflictError(f"Teacher with email {update_data['email']} already exists")
    
    for field, value in update_data.items():
        setattr(teacher, field, value)
    
    db.commit()
    db.refresh(teacher)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            teacher_name = f"{teacher.firstname} {teacher.lastname} ({teacher.employee_id})"
            institution_id = getattr(teacher, 'institution_id', None) or (current_user.institution_id if current_user else None)
            if institution_id:
                log_update_activity(
                    db=db,
                    current_user=current_user,
                    entity_type="teacher",
                    entity_id=teacher.id,
                    entity_name=teacher_name,
                    institution_id=institution_id,
                    content=f"Updated teacher: {teacher_name}"
                )
        except Exception as e:
            print(f"Error logging teacher update activity: {e}")
    
    return teacher


def delete_teacher(db: Session, teacher_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a teacher"""
    teacher = get_teacher(db, teacher_id)
    teacher_name = f"{teacher.firstname} {teacher.lastname} ({teacher.employee_id})"
    institution_id = getattr(teacher, 'institution_id', None) or (current_user.institution_id if current_user else None)
    from datetime import datetime
    teacher.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user and institution_id:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="teacher",
                entity_id=teacher_id,
                entity_name=teacher_name,
                institution_id=institution_id,
                content=f"Deleted teacher: {teacher_name}"
            )
        except Exception as e:
            print(f"Error logging teacher deletion activity: {e}")
    
    return True


def get_teacher_by_email(db: Session, email: str) -> Optional[Teacher]:
    """Get teacher by email"""
    return db.query(Teacher).filter(
        Teacher.email == email,
        Teacher.deleted_at.is_(None)
    ).first()


def get_teacher_by_employee_id(db: Session, employee_id: str) -> Optional[Teacher]:
    """Get teacher by employee ID"""
    return db.query(Teacher).filter(
        Teacher.employee_id == employee_id,
        Teacher.deleted_at.is_(None)
    ).first()


def get_teacher_by_user_id(db: Session, user_id: int) -> Optional[Teacher]:
    """Get teacher by user ID (via email matching)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return db.query(Teacher).filter(
        Teacher.email == user.email,
        Teacher.deleted_at.is_(None)
    ).first()
