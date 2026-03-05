from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentRequest, StudentResponse, StudentUpdate
from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity, get_user_display_name
from app.apis.tenant_settings import generate_student_id, is_matricule_format_configured
import datetime

def create_student(db: Session, student: StudentRequest, institution_id: Optional[int] = None, current_user: Optional[User] = None) -> Student:
    """Create a new student"""
    # Use institution_id from request body if provided, otherwise use the parameter
    final_institution_id = getattr(student, 'institution_id', None) or institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required to create a student")
    
    # Check if email already exists within the same institution
    existing = db.query(Student).filter(
        Student.email == student.email,
        Student.institution_id == final_institution_id,
        Student.deleted_at.is_(None)
    ).first()
    if existing:
        raise ConflictError(f"Student with email {student.email} already exists")
    
    # Generate student_id if not provided or empty
    student_id_to_use = student.student_id
    if not student_id_to_use or student_id_to_use.strip() == '':
        # Check if matricule format is configured
        if not is_matricule_format_configured(db, final_institution_id):
            raise ValidationError(
                "Matricule format is not configured. Please configure it in Tenant Settings before creating students."
            )
        
        # Generate student_id using configured format
        student_data_dict = {
            'class_id': student.class_id,
            'department_id': student.department_id,
            'academic_year_id': student.academic_year_id,
            'academic_year': datetime.datetime.now().year  # Default to current year
        }
        student_id_to_use = generate_student_id(db, final_institution_id, student_data_dict)
    
    # Check if student_id already exists within the same institution
    existing = db.query(Student).filter(
        Student.student_id == student_id_to_use,
        Student.institution_id == final_institution_id,
        Student.deleted_at.is_(None)
    ).first()
    if existing:
        raise ConflictError(f"Student with student_id {student_id_to_use} already exists")
    
    # Update student object with generated/validated student_id
    student.student_id = student_id_to_use
    
    # Handle guardian creation or validation
    from app.models.guardian import Guardian
    guardian_id = student.guardian_id
    
    # If guardian information is provided but no guardian_id, create a new guardian
    if not guardian_id and student.guardian_name:
        # Create new guardian
        new_guardian = Guardian(
            institution_id=final_institution_id,
            guardian_name=student.guardian_name,
            phone=student.guardian_phone or '',
            address=student.guardian_address or student.address or '',
            relationship=student.guardian_relationship or 'parent',
            gender=student.guardian_gender or 'Male',
            email=student.guardian_email,
            occupation=student.guardian_occupation
        )
        db.add(new_guardian)
        db.flush()  # Flush to get the ID without committing
        guardian_id = new_guardian.id
    elif guardian_id:
        # Verify guardian exists and belongs to the same institution
        guardian = db.query(Guardian).filter(
            Guardian.id == guardian_id,
            Guardian.institution_id == final_institution_id,
            Guardian.deleted_at.is_(None)
        ).first()
        if not guardian:
            raise NotFoundError(f"Guardian with ID {guardian_id} not found for this institution")
    else:
        # No guardian_id and no guardian info - create a default guardian
        default_guardian = Guardian(
            institution_id=final_institution_id,
            guardian_name=f"{student.firstname} {student.lastname} - Guardian",
            phone=student.phone,
            address=student.address,
            relationship='guardian',
            gender='Unknown'
        )
        db.add(default_guardian)
        db.flush()
        guardian_id = default_guardian.id
    
    # Prepare student data (exclude guardian fields and institution_id from student dict)
    # institution_id will be set explicitly
    student_dict = student.dict(exclude={
        'guardian_name', 'guardian_phone', 'guardian_address', 
        'guardian_relationship', 'guardian_gender', 'guardian_email', 'guardian_occupation',
        'institution_id','photo'  # Exclude if present, we'll set it explicitly
    })
    student_dict['institution_id'] = final_institution_id
    student_dict['guardian_id'] = guardian_id
    
    new_student = Student(**student_dict)
    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    new_student.photo = student.photo
    
    # Log activity if current_user is provided
    if current_user:
        try:
            student_name = f"{student.firstname} {student.lastname} ({student.student_id})"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="student",
                entity_id=new_student.id,
                entity_name=student_name,
                institution_id=final_institution_id,
                content=f"Created student: {student_name}"
            )
        except Exception as e:
            # Don't fail the operation if activity logging fails
            print(f"Error logging student creation activity: {e}")
    
    # Send registration email to student asynchronously (non-blocking)
    if student.email:
        try:
            from app.services.email_service import EmailService
            from app.helpers.async_helper import run_async_safe
            from app.models.tenant import Tenant
            
            # Get institution name if available
            institution_name = None
            try:
                from app.database.base import get_db_session
                global_db = next(get_db_session())
                try:
                    tenant = global_db.query(Tenant).filter(Tenant.id == final_institution_id).first()
                    if tenant:
                        institution_name = tenant.name
                finally:
                    global_db.close()
            except Exception:
                pass  # If we can't get institution name, continue without it
            
            student_full_name = f"{student.firstname} {student.lastname}"
            run_async_safe(
                EmailService.send_student_registration_email(
                    student_name=student_full_name,
                    student_email=student.email,
                    student_id=student.student_id,
                    institution_name=institution_name
                )
            )
        except Exception as e:
            # Don't fail the operation if email sending fails
            from app.helpers.logger import logger
            logger.error(f"Error sending registration email to student {student.email}: {e}")
    
    return new_student


def get_student(db: Session, student_id: int, institution_id: Optional[int] = None) -> Student:
    """Get a student by ID (tenant-scoped if institution_id is provided)"""
    userQuery = db.query(User).filter(
        User.id == student_id,
        User.deleted_at.is_(None)
    ).first()
    query = db.query(Student).filter(
        Student.institution_id == userQuery.institution_id,
        Student.deleted_at.is_(None)
    )
    if institution_id is not None:
        query = query.filter(Student.institution_id == institution_id)
    student = query.first()
    if not student:
        raise NotFoundError(f"Student with ID {student_id} not found")
    return student


def get_students(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None,
    class_id: Optional[int] = None,
    department_id: Optional[int] = None,
    academic_year_id: Optional[int] = None
) -> tuple[List[Student], int]:
    """Get list of students with pagination"""
    query = db.query(Student).filter(Student.deleted_at.is_(None))
    
    # Filter by institution_id if provided (required for multi-tenancy)
    # If institution_id is None, this might be a system admin viewing all students
    # For tenant users, institution_id should always be provided
    if institution_id is not None:
        query = query.filter(Student.institution_id == institution_id)
    
    if class_id:
        query = query.filter(Student.class_id == class_id)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if academic_year_id:
        query = query.filter(Student.academic_year_id == academic_year_id)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def update_student(db: Session, student_id: int, student_update: StudentUpdate, current_user: Optional[User] = None) -> Student:
    """Update a student"""
    student = get_student(db, student_id)
    
    update_data = student_update.dict(exclude_unset=True)
    
    # Check email uniqueness if being updated
    if "email" in update_data:
        existing = db.query(Student).filter(
            Student.email == update_data["email"],
            Student.id != student_id
        ).first()
        if existing:
            raise ConflictError(f"Student with email {update_data['email']} already exists")
    
    # Check student_id uniqueness if being updated
    if "student_id" in update_data:
        existing = db.query(Student).filter(
            Student.student_id == update_data["student_id"],
            Student.id != student_id
        ).first()
        if existing:
            raise ConflictError(f"Student with student_id {update_data['student_id']} already exists")
    
    for field, value in update_data.items():
        setattr(student, field, value)
    
    db.commit()
    db.refresh(student)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            student_name = f"{student.firstname} {student.lastname} ({student.student_id})"
            institution_id = student.institution_id or current_user.institution_id
            if institution_id:  # Only log if we have an institution_id
                log_update_activity(
                    db=db,
                    current_user=current_user,
                    entity_type="student",
                    entity_id=student.id,
                    entity_name=student_name,
                    institution_id=institution_id,
                    content=f"Updated student: {student_name}"
                )
        except Exception as e:
            # Don't fail the operation if activity logging fails
            print(f"Error logging student update activity: {e}")
    
    return student


def delete_student(db: Session, student_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a student"""
    student = get_student(db, student_id)
    student_name = f"{student.firstname} {student.lastname} ({student.student_id})"
    institution_id = student.institution_id
    from datetime import datetime
    student.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="student",
                entity_id=student_id,
                entity_name=student_name,
                institution_id=institution_id,
                content=f"Deleted student: {student_name}"
            )
        except Exception as e:
            # Don't fail the operation if activity logging fails
            print(f"Error logging student deletion activity: {e}")
    
    return True


def get_student_by_email(db: Session, email: str) -> Optional[Student]:
    """Get student by email"""
    return db.query(Student).filter(
        Student.email == email,
        Student.deleted_at.is_(None)
    ).first()


def get_student_by_student_id(db: Session, student_id: str) -> Optional[Student]:
    """Get student by student registration ID"""
    return db.query(Student).filter(
        Student.student_id == student_id,
        Student.deleted_at.is_(None)
    ).first()