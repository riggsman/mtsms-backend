from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentRequest, StudentResponse, StudentUpdate
from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity, get_user_display_name
from app.apis.tenant_settings import generate_student_id, is_matricule_format_configured
from app.apis.classes import check_classes_configured
import datetime
import os
import uuid
import re
import base64
from pathlib import Path
from app.helpers.logger import *
from fastapi import HTTPException, status


async def save_student_photo(base64_photo: str, institution_id: int, student_id: str) -> Optional[str]:
    """
    Save base64 encoded photo to uploads/student_photos directory and return relative path.
    
    Args:
        base64_photo: Base64 encoded photo string (data:image/...;base64,...)
        institution_id: Institution ID for tenant scoping
        student_id: Student ID for naming the file
        
    Returns:
        Relative path to saved photo or None if no photo provided
    """
    if not base64_photo or not base64_photo.strip():
        return None
    
    if not base64_photo.startswith('data:image/'):
        return base64_photo
    
    try:
        tenant_domain = "default"
        try:
            from app.models.tenant import Tenant
            from app.database.base import get_db_session
            global_db = next(get_db_session())
            try:
                tenant = global_db.query(Tenant).filter(Tenant.id == institution_id).first()
                if tenant and tenant.domain:
                    tenant_domain = tenant.domain
            finally:
                global_db.close()
        except Exception:
            pass
        
        from app.helpers.file_upload import sanitize_domain
        sanitized_domain = sanitize_domain(tenant_domain)
        
        header, encoded = base64_photo.split(',', 1)
        image_data = base64.b64decode(encoded)
        
        file_ext = '.jpg'
        if 'png' in header:
            file_ext = '.png'
        elif 'gif' in header:
            file_ext = '.gif'
        elif 'webp' in header:
            file_ext = '.webp'
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{sanitized_domain}_student_{student_id}_{timestamp}_{unique_id}{file_ext}"
        
        upload_dir = os.path.join(os.getcwd(), 'uploads', 'student_photos')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        relative_path = os.path.join('student_photos', filename).replace('\\', '/')
        return relative_path
        
    except Exception as e:
        print(f"Error saving student photo: {e}")
        return None


def save_student_photo_sync(base64_photo: str, institution_id: int, student_id: str) -> Optional[str]:
    """
    Synchronous version of save_student_photo for use in sync contexts.
    """
    if not base64_photo or not base64_photo.strip():
        return None
    
    if not base64_photo.startswith('data:image/'):
        return base64_photo
    
    try:
        tenant_domain = "default"
        try:
            from app.models.tenant import Tenant
            from app.database.base import get_db_session
            global_db = next(get_db_session())
            try:
                tenant = global_db.query(Tenant).filter(Tenant.id == institution_id).first()
                if tenant and tenant.domain:
                    tenant_domain = tenant.domain
            finally:
                global_db.close()
        except Exception:
            pass
        
        from app.helpers.file_upload import sanitize_domain
        sanitized_domain = sanitize_domain(tenant_domain)
        
        header, encoded = base64_photo.split(',', 1)
        image_data = base64.b64decode(encoded)
        
        file_ext = '.jpg'
        if 'png' in header:
            file_ext = '.png'
        elif 'gif' in header:
            file_ext = '.gif'
        elif 'webp' in header:
            file_ext = '.webp'
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{sanitized_domain}_student_{student_id}_{timestamp}_{unique_id}{file_ext}"
        
        upload_dir = os.path.join(os.getcwd(), 'uploads', 'student_photos')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        relative_path = os.path.join('student_photos', filename).replace('\\', '/')
        return relative_path
        
    except Exception as e:
        print(f"Error saving student photo: {e}")
        return None

def create_student(db: Session, student: StudentRequest, institution_id: Optional[int] = None, current_user: Optional[User] = None) -> Student:
    """Create a new student"""
    # Use institution_id from request body if provided, otherwise use the parameter
    final_institution_id = getattr(student, 'institution_id', None) or institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required to create a student")
    
    # Check if classes are configured for this institution
    if not check_classes_configured(db, final_institution_id):
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Classes have not been configured for institution wiwth id {final_institution_id}.")
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Classes have not been configured for this institution."
        )
        # raise ValidationError(
        #     "Classes have not been configured for this institution. "
        #     "Please configure classes before registering students."
        # )
    
    # Check if email already exists within the same institution
    existing = db.query(Student).filter(
        Student.email == student.email,
        Student.institution_id == final_institution_id,
        Student.deleted_at.is_(None)
    ).first()
    if existing:
        error(f"Student with email {student.email} already exists")
        raise ConflictError(f"Student with email {student.email} already exists")
    
    # Generate student_id if not provided or empty
    student_id_to_use = student.student_id
    if not student_id_to_use or student_id_to_use.strip() == '':
        # Check if matricule format is configured
        if not is_matricule_format_configured(db, final_institution_id):
            raise ValidationError(
                "Matricule format is not configured. Please configure it in Tenant Settings before creating students."
            )
        
        # Fetch school, branch, and department codes for matricule generation
        school_initial = ''
        branch_initial = ''
        department_code = ''
        
        # Get school code
        if student.school_id:
            from app.models.school import School
            school = db.query(School).filter(School.id == student.school_id).first()
            if school and school.code:
                school_initial = school.code.strip().upper()[:3]
        
        # Get branch initial (only if branch is provided)
        if student.branch_id:
            from app.models.branch import Branch
            branch = db.query(Branch).filter(Branch.id == student.branch_id).first()
            if branch and branch.name:
                branch_initial = branch.name.strip()[0].upper()
        
        # Get department code
        if student.department_id:
            from app.models.department import Department
            dept = db.query(Department).filter(Department.id == student.department_id).first()
            if dept and dept.code:
                department_code = dept.code.strip().upper()
        
        # Generate student_id using configured format
        student_data_dict = {
            'class_id': student.class_id,
            'department_id': student.department_id,
            'academic_year_id': student.academic_year_id,
            'academic_year': datetime.datetime.now().year,  # Default to current year
            'school_id': student.school_id,
            'branch_id': student.branch_id,
            'school_initial': school_initial,
            'branch_initial': branch_initial,
            'department_code': department_code
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

    if student.photo:
        try:
            photo_path = save_student_photo_sync(student.photo, final_institution_id, student.student_id)
            if photo_path:
                new_student.photo = photo_path
                db.commit()
                db.refresh(new_student)
        except Exception as e:
            print(f"Error saving photo: {e}")
    
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
    
    try:
        from app.apis.parent_accounts import sync_parent_user_for_guardian
        from app.services.email_service import EmailService
        from app.helpers.async_helper import run_async_safe
        from app.models.tenant import Tenant

        plain_pw = sync_parent_user_for_guardian(
            db,
            institution_id=final_institution_id,
            guardian_email=student.guardian_email,
            guardian_name=student.guardian_name,
            guardian_phone=student.guardian_phone,
            guardian_address=student.guardian_address or student.address,
        )
        db.commit()
        if plain_pw and student.guardian_email:
            try:
                inst_name = None
                trow = db.query(Tenant).filter(Tenant.id == final_institution_id).first()
                if trow:
                    inst_name = trow.name
                parent_nm = (student.guardian_name or "").strip() or "Parent"
                u = (
                    db.query(User)
                    .filter(
                        func.lower(User.email) == (student.guardian_email or "").strip().lower(),
                        User.deleted_at.is_(None),
                    )
                    .first()
                )
                uname = u.username if u else (student.guardian_email or "").strip()
                run_async_safe(
                    EmailService.send_parent_portal_welcome_email(
                        parent_name=parent_nm,
                        parent_email=(student.guardian_email or "").strip(),
                        username=uname,
                        password=plain_pw,
                        institution_name=inst_name,
                    )
                )
            except Exception as mail_exc:
                import logging

                logging.getLogger(__name__).warning("Parent welcome email failed: %s", mail_exc)
    except Exception as e:
        db.rollback()
        import logging

        logging.getLogger(__name__).warning("Parent account sync skipped or failed: %s", e)

    return new_student


def resolve_student_for_logged_in_user(db: Session, current_user: User) -> Optional[Student]:
    """
    Resolve the Student record for the authenticated user (same institution).

    Tries, in order:
    1) Case-insensitive match on User.email vs Student.email
    2) Student.student_id (matricule) == User.username (common login pattern)
    3) Case-insensitive match on User.username vs Student.email (edge cases)
    """
    if not current_user or not current_user.institution_id:
        return None

    institution_id = current_user.institution_id
    base = db.query(Student).filter(
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None),
    )

    email_norm = (current_user.email or "").strip()
    if email_norm:
        row = base.filter(func.lower(Student.email) == email_norm.lower()).first()
        if row:
            return row

    username_norm = (current_user.username or "").strip()
    if username_norm:
        row = base.filter(Student.student_id == username_norm).first()
        if row:
            return row
        row = base.filter(func.lower(Student.email) == username_norm.lower()).first()
        if row:
            return row

    return None


def get_student(db: Session, student_id: int, institution_id: Optional[int] = None) -> Student:
    """Get a student by primary key (tenant-scoped when institution_id is provided)."""
    query = db.query(Student).filter(
        Student.id == student_id,
        Student.deleted_at.is_(None),
    )
    if institution_id is not None:
        query = query.filter(Student.institution_id == institution_id)
    student = query.first()
    if not student:
        raise NotFoundError(f"Student with ID {student_id} not found")

    # Enrich detail payload with human-readable linked data so the frontend
    # can render student details directly from one server response.
    try:
        from app.models.guardian import Guardian
        guardian = (
            db.query(Guardian)
            .filter(
                Guardian.id == student.guardian_id,
                Guardian.deleted_at.is_(None),
            )
            .first()
        )
        if guardian:
            setattr(student, "guardian_name", guardian.guardian_name)
            setattr(student, "guardian_phone", guardian.phone)
            setattr(student, "guardian_address", guardian.address)
            setattr(student, "guardian_relationship", guardian.relationship)
            setattr(student, "guardian_gender", guardian.gender)
            setattr(student, "guardian_email", guardian.email)
            setattr(student, "guardian_occupation", guardian.occupation)
    except Exception:
        pass

    try:
        from app.models.branch import Branch
        if student.branch_id:
            branch = (
                db.query(Branch)
                .filter(Branch.id == student.branch_id)
                .first()
            )
            if branch:
                setattr(student, "branch_name", branch.name)
    except Exception:
        pass

    try:
        from app.models.classes import Class
        class_row = (
            db.query(Class)
            .filter(Class.id == student.class_id, Class.deleted_at.is_(None))
            .first()
        )
        if class_row:
            setattr(student, "class_name", class_row.name or class_row.class_name)
    except Exception:
        pass

    try:
        from app.models.department import Department
        dept = (
            db.query(Department)
            .filter(Department.id == student.department_id, Department.deleted_at.is_(None))
            .first()
        )
        if dept:
            setattr(student, "department_name", dept.name)
    except Exception:
        pass

    try:
        from app.models.specialty import Specialization
        if student.specialization_id:
            specialization = (
                db.query(Specialization)
                .filter(
                    Specialization.id == student.specialization_id,
                    Specialization.deleted_at.is_(None),
                )
                .first()
            )
            if specialization:
                setattr(student, "specialization_name", specialization.name)
    except Exception:
        pass

    try:
        from app.models.school import School
        school = (
            db.query(School)
            .filter(School.id == student.school_id, School.deleted_at.is_(None))
            .first()
        )
        if school:
            setattr(student, "school_name", school.name)
    except Exception:
        pass

    return student


def get_students(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None,
    class_id: Optional[int] = None,
    department_id: Optional[int] = None,
    academic_year_id: Optional[int] = None,
    branch_id: Optional[int] = None,
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
    if branch_id is not None:
        query = query.filter(Student.branch_id == branch_id)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def update_student(db: Session, student_id: int, student_update: StudentUpdate, current_user: Optional[User] = None) -> Student:
    """Update a student"""
    from app.helpers.user_roles import user_requires_tenant_scope_for_data

    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id

    student = get_student(db, student_id, institution_id=institution_id)

    update_data = student_update.model_dump(exclude_unset=True) if hasattr(student_update, "model_dump") else student_update.dict(exclude_unset=True)
    
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
    
    photo_value = update_data.pop('photo', None)
    
    for field, value in update_data.items():
        setattr(student, field, value)
    
    if photo_value:
        try:
            photo_path = save_student_photo_sync(photo_value, student.institution_id, student.student_id)
            if photo_path:
                student.photo = photo_path
        except Exception as e:
            print(f"Error saving photo: {e}")
    
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
    from app.helpers.user_roles import user_requires_tenant_scope_for_data

    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id

    student = get_student(db, student_id, institution_id=institution_id)
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