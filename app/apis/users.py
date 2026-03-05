from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from app.models.user import User
from app.exceptions import NotFoundError, ConflictError
from app.helpers.pagination import paginate_query
from app.schemas.users import UserRequest, UserUpdate
from app.authentication.authenticator import hash_password, validate_password_strength
from app.exceptions import ValidationError
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity, get_user_display_name
from app.apis.activity import log_activity
from app.services.email_service import EmailService
from app.helpers.async_helper import run_async_safe
from datetime import datetime

logger = logging.getLogger(__name__)

def create_user(db: Session, user: UserRequest, creator_user: Optional[User] = None) -> User:
    """
    Create a new user
    user_type is determined by the creator:
    - If creator has system_ role -> user_type = "SYSTEM"
    - Otherwise -> user_type = "TENANT"
    """
    # Validate password strength
    is_valid, error_msg = validate_password_strength(user.password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # Check if username already exists
    existing_user = get_user_by_username(db, user.username)
    if existing_user:
        raise ConflictError("Username already registered")
    
    # Check if email already exists
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise ConflictError("Email already registered")
    
    # Determine user_type based on creator's role
    user_type = "TENANT"  # Default to TENANT
    if creator_user and creator_user.role and creator_user.role.startswith('system_'):
        user_type = "SYSTEM"
    
    # Hash password
    hashed_password = hash_password(user.password)
    
    # Create new user
    new_user = User(
        institution_id=user.institution_id,
        firstname=user.firstname,
        middlename=user.middlename,
        lastname=user.lastname,
        gender=user.gender,
        address=user.address,
        email=user.email,
        phone=user.phone,
        username=user.username,
        password=hashed_password,
        role=user.role,
        user_type=user_type,
        is_active=user.is_active or "active",
        must_change_password=getattr(user, 'must_change_password', 'false')
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log activity if creator_user is provided
    if creator_user:
        try:
            log_create_activity(
                db=db,
                current_user=creator_user,
                entity_type="user",
                entity_id=new_user.id,
                entity_name=f"{new_user.firstname} {new_user.lastname} ({new_user.username})".strip(),
                institution_id=new_user.institution_id
            )
        except Exception as e:
            # Don't fail the operation if activity logging fails
            pass
    
    # Send registration email asynchronously with tracking
    try:
        from app.helpers.async_helper import run_async_safe
        from app.services.email_tracker import EmailTracker
        # Get tenant/institution name and login URL from tenant domain
        institution_name = None
        login_url = None
        try:
            from app.database.base import get_db_session
            global_db = next(get_db_session())
            try:
                from app.models.tenant import Tenant
                tenant = global_db.query(Tenant).filter(
                    Tenant.database_name == db.bind.url.database
                ).first()
                if tenant:
                    institution_name = tenant.name
                    if tenant.domain:
                        login_url = f"https://{tenant.domain}"
            except Exception as tenant_error:
                logger.warning(f"Error getting tenant info: {tenant_error}")
            finally:
                global_db.close()
        except Exception as db_error:
            logger.warning(f"Error accessing global database: {db_error}")
        
        # Determine user type for email
        user_full_name = f"{new_user.firstname} {new_user.lastname}".strip()
        roles_list = new_user.role.split(',') if ',' in new_user.role else [new_user.role]
        is_student = 'student' in roles_list
        
        # Send email with tracking - use wrapper that calls EmailService methods
        async def send_tracked_email():
            if is_student:
                # Use student registration email with tracking
                from app.services.email_tracker import EmailTracker
                from app.conf.config import settings
                
                # Get email content from EmailService
                html_content, text_content = await EmailService._get_student_registration_email_content(
                    student_name=user_full_name,
                    student_email=new_user.email,
                    student_id=new_user.username,
                    password=user.password,
                    must_change_password=new_user.must_change_password == "true",
                    institution_name=institution_name,
                    login_url=login_url
                )
                subject = f"{settings.APP_NAME} - Student Account Registration"
                
                await EmailTracker.send_with_tracking(
                    db=db,
                    sender_email=settings.SMTP_FROM_EMAIL,
                    recipient_email=new_user.email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    institution_id=new_user.institution_id
                )
            else:
                # Use staff registration email with tracking
                from app.services.email_tracker import EmailTracker
                from app.conf.config import settings
                
                # Get email content from EmailService
                html_content, text_content = await EmailService._get_lecturer_registration_email_content(
                    lecturer_name=user_full_name,
                    lecturer_email=new_user.email,
                    username=new_user.username,
                    password=user.password,
                    employee_id=new_user.username,
                    institution_name=institution_name,
                    login_url=login_url,
                    must_change_password=new_user.must_change_password == "true"
                )
                subject = f"{settings.APP_NAME} - Staff Account Created"
                
                await EmailTracker.send_with_tracking(
                    db=db,
                    sender_email=settings.SMTP_FROM_EMAIL,
                    recipient_email=new_user.email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    institution_id=new_user.institution_id
                )
        
        run_async_safe(send_tracked_email())
    except Exception as e:
        # Don't fail user creation if email sending fails
        logger.error(f"Error sending registration email to user {new_user.email}: {e}")
    
    return new_user

def get_user(db: Session, user_id: int) -> User:
    """Get a user by ID"""
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None)
    ).first()
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    return user


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    role: Optional[str] = None,
    institution_id: Optional[int] = None,
    exclude_role: Optional[str] = None
) -> tuple[List[User], int]:
    """Get list of users with pagination"""
    query = db.query(User).filter(User.deleted_at.is_(None))
    
    if role:
        query = query.filter(User.role == role)
    if exclude_role:
        query = query.filter(User.role != exclude_role)
    if institution_id:
        query = query.filter(User.institution_id == institution_id)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(
        User.username == username,
        User.deleted_at.is_(None)
    ).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(
        User.email == email,
        User.deleted_at.is_(None)
    ).first()

def update_user(db: Session, user_id: int, user_update: UserUpdate, current_user: Optional[User] = None) -> User:
    """Update a user"""
    user = get_user(db, user_id)
    
    update_data = user_update.dict(exclude_unset=True)
    
    # If password is being updated, validate and hash it
    if "password" in update_data and update_data["password"]:
        is_valid, error_msg = validate_password_strength(update_data["password"])
        if not is_valid:
            raise ValidationError(error_msg)
        update_data["password"] = hash_password(update_data["password"])
    
    # Check if username is being changed and if it's already taken
    if "username" in update_data and update_data["username"] != user.username:
        existing_user = get_user_by_username(db, update_data["username"])
        if existing_user:
            raise ConflictError("Username already taken")
    
    # Check if email is being changed and if it's already taken
    if "email" in update_data and update_data["email"] != user.email:
        existing_user = get_user_by_email(db, update_data["email"])
        if existing_user:
            raise ConflictError("Email already taken")
    
    # Update fields
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)

    email_service = EmailService()
    EmailService().send_user_update_email(user)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="user",
                entity_id=user.id,
                entity_name=f"{user.firstname} {user.lastname} ({user.username})".strip(),
                institution_id=user.institution_id
            )
        except Exception as e:
            # Don't fail the operation if activity logging fails
            pass
    
    return user

def delete_user(db: Session, user_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a user"""
    user = get_user(db, user_id)
    entity_name = f"{user.firstname} {user.lastname} ({user.username})".strip()
    institution_id = user.institution_id
    
    user.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="user",
                entity_id=user.id,
                entity_name=entity_name,
                institution_id=institution_id
            )
        except Exception as e:
            # Don't fail the operation if activity logging fails
            pass
    
    return True

def assign_student_password(db: Session, student_id: int, password: str, username: Optional[str] = None, institution_id: int = None) -> User:
    """Assign password to a student by creating or updating their user account"""
    from app.models.student import Student
    
    # Get student by ID
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.deleted_at.is_(None)
    ).first()
    
    if not student:
        raise NotFoundError(f"Student with ID {student_id} not found")
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # Hash password
    hashed_password = hash_password(password)
    
    # Check if user account already exists for this student (by email)
    existing_user = get_user_by_email(db, student.email)
    
    if existing_user:
        # Update existing user account
        existing_user.password = hashed_password
        existing_user.must_change_password = "true"  # Force password change on next login
        if username:
            # Check if username is already taken by another user
            other_user = get_user_by_username(db, username)
            if other_user and other_user.id != existing_user.id:
                raise ConflictError("Username already taken")
            existing_user.username = username
        db.commit()
        db.refresh(existing_user)
        
        # Send password assignment email asynchronously (non-blocking)
        try:
            from app.helpers.async_helper import run_async_safe
            # Get tenant/institution name and login URL from tenant domain
            institution_name = None
            login_url = None
            try:
                from app.database.base import get_db_session
                global_db = next(get_db_session())
                try:
                    from app.models.tenant import Tenant
                    tenant = global_db.query(Tenant).filter(
                        Tenant.database_name == db.bind.url.database
                    ).first()
                    if tenant:
                        institution_name = tenant.name  # Use tenant name as institution name
                        if tenant.domain:
                            login_url = f"https://{tenant.domain}"
                except Exception as tenant_error:
                    logger.warning(f"Error getting tenant info: {tenant_error}")
                finally:
                    global_db.close()
            except Exception as db_error:
                logger.warning(f"Error accessing global database: {db_error}")
            
            # Send password assignment email with tracking
            async def send_password_email():
                from app.services.email_tracker import EmailTracker
                from app.conf.config import settings
                
                html_content, text_content = await EmailService._get_student_password_assignment_email_content(
                    student_name=f"{student.firstname} {student.lastname}".strip(),
                    student_email=student.email,
                    student_id=student.student_id or str(student.id),
                    username=existing_user.username,
                    password=password,
                    must_change_password=True,
                    institution_name=institution_name,
                    login_url=login_url
                )
                subject = f"{settings.APP_NAME} - Your Account Password Has Been Assigned"
                
                await EmailTracker.send_with_tracking(
                    db=db,
                    sender_email=settings.SMTP_FROM_EMAIL,
                    recipient_email=student.email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    institution_id=institution_id or existing_user.institution_id
                )
            
            run_async_safe(send_password_email())
        except Exception as e:
            # Don't fail password assignment if email sending fails
            logger.error(f"Error sending password assignment email to student {student.email}: {e}")
        
        return existing_user
    else:
        # Create new user account for student
        if not institution_id:
            raise ValidationError("institution_id is required to create user account")
        
        # Generate username if not provided
        if not username:
            username = student.student_id or student.email.split('@')[0]
        
        # Check if username already exists
        if get_user_by_username(db, username):
            username = f"{username}_{student.id}"  # Append student ID if username exists
        
        new_user = User(
            institution_id=institution_id,
            firstname=student.firstname,
            middlename=student.middlename,
            lastname=student.lastname,
            gender=student.gender,
            address=student.address,
            email=student.email,
            phone=student.phone,
            username=username,
            password=hashed_password,
            role="student",
            user_type="TENANT",  # Students are always TENANT users
            is_active="active",
            must_change_password="true"  # Student must change password on first login
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send password assignment email asynchronously (non-blocking)
        try:
            from app.helpers.async_helper import run_async_safe
            # Get tenant/institution name and login URL from tenant domain
            institution_name = None
            login_url = None
            try:
                from app.database.base import get_db_session
                global_db = next(get_db_session())
                try:
                    from app.models.tenant import Tenant
                    tenant = global_db.query(Tenant).filter(
                        Tenant.database_name == db.bind.url.database
                    ).first()
                    if tenant:
                        institution_name = tenant.name  # Use tenant name as institution name
                        if tenant.domain:
                            login_url = f"https://{tenant.domain}"
                except Exception as tenant_error:
                    logger.warning(f"Error getting tenant info: {tenant_error}")
                finally:
                    global_db.close()
            except Exception as db_error:
                logger.warning(f"Error accessing global database: {db_error}")
            
            # Send password assignment email with tracking
            async def send_password_email():
                from app.services.email_tracker import EmailTracker
                from app.conf.config import settings
                
                html_content, text_content = await EmailService._get_student_password_assignment_email_content(
                    student_name=f"{student.firstname} {student.lastname}".strip(),
                    student_email=student.email,
                    student_id=student.student_id or str(student.id),
                    username=new_user.username,
                    password=password,
                    must_change_password=True,
                    institution_name=institution_name,
                    login_url=login_url
                )
                subject = f"{settings.APP_NAME} - Your Account Password Has Been Assigned"
                
                await EmailTracker.send_with_tracking(
                    db=db,
                    sender_email=settings.SMTP_FROM_EMAIL,
                    recipient_email=student.email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    institution_id=institution_id or new_user.institution_id
                )
            
            run_async_safe(send_password_email())
        except Exception as e:
            # Don't fail password assignment if email sending fails
            logger.error(f"Error sending password assignment email to student {student.email}: {e}")
        
        return new_user

def change_password(db: Session, user_id: int, current_password: str, new_password: str, current_user: Optional[User] = None) -> User:
    """Change user password (for first-time login or regular password change)"""
    from app.authentication.authenticator import verify_password
    
    user = get_user(db, user_id)
    
    # Verify current password
    # Handle case where password might be None or empty
    if not user.password:
        raise ValidationError("User password not set. Please contact administrator.")
    
    # Debug: Log hash format (first 30 chars only for security)
    print(f"Debug: Verifying password for user {user_id} (username: {user.username})")
    print(f"Debug: Hash prefix: {str(user.password)[:30]}...")
    
    try:
        password_verified = verify_password(current_password, user.password)
    except Exception as e:
        # Log the error for debugging but don't expose internal details
        print(f"Error verifying password for user {user_id}: {type(e).__name__}: {e}")
        raise ValidationError("Error verifying current password. Please try again or contact administrator.")
    
    if not password_verified:
        print(f"Password verification failed for user {user_id}")
        raise ValidationError("Current password is incorrect. Please check your password and try again.")
    
    # Validate new password strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # Hash and update password
    user.password = hash_password(new_password)
    # Set must_change_password to false when password is changed (user has successfully changed their password)
    user.must_change_password = "false"
    db.commit()
    db.refresh(user)
    
    # Fix invalid datetime values before returning (handle '0000-00-00 00:00:00' from MySQL)
    if user.created_at is not None:
        if hasattr(user.created_at, 'year') and user.created_at.year == 0:
            user.created_at = None
        elif isinstance(user.created_at, str) and user.created_at.startswith('0000-00-00'):
            user.created_at = None
    if user.updated_at is not None:
        if hasattr(user.updated_at, 'year') and user.updated_at.year == 0:
            user.updated_at = None
        elif isinstance(user.updated_at, str) and user.updated_at.startswith('0000-00-00'):
            user.updated_at = None
    if hasattr(user, 'deleted_at') and user.deleted_at is not None:
        if hasattr(user.deleted_at, 'year') and user.deleted_at.year == 0:
            user.deleted_at = None
        elif isinstance(user.deleted_at, str) and user.deleted_at.startswith('0000-00-00'):
            user.deleted_at = None
    
    # Log activity if current_user is provided
    # Use the user who is changing the password (could be themselves or an admin)
    performer = current_user if current_user else user
    institution_id = user.institution_id if user.institution_id else (performer.institution_id if performer else None)
    
    if institution_id:
        try:
            user_display_name = get_user_display_name(user)
            performer_display_name = get_user_display_name(performer)
            
            # Determine if user is changing their own password or an admin is changing it
            is_self_change = performer.id == user.id
            if is_self_change:
                content = f"User {user_display_name} changed their password"
            else:
                content = f"Admin {performer_display_name} changed password for user {user_display_name}"
            
            log_activity(
                db=db,
                institution_id=institution_id,
                action="Password Changed",
                entity_type="user",
                entity_id=user.id,
                performed_by=performer_display_name,
                performer_role=performer.role,
                performer_id=performer.id,
                content=content
            )
        except Exception as e:
            print(f"Error logging password change activity: {e}")
    
    # Send password change notification email asynchronously (non-blocking)
    if user.email:
        try:
            user_display_name = get_user_display_name(user)
            is_admin_change = performer.id != user.id if performer else False
            admin_name = get_user_display_name(performer) if is_admin_change else None
            
            run_async_safe(
                EmailService.send_password_change_email(
                    user_name=user_display_name,
                    user_email=user.email,
                    changed_by_admin=is_admin_change,
                    admin_name=admin_name
                )
            )
        except Exception as e:
            # Don't fail password change if email sending fails
            print(f"Error sending password change email: {e}")
    
    return user

def suspend_user(db: Session, user_id: int, reason: str, current_user: Optional[User] = None) -> User:
    """Suspend a user account"""
    from app.models.student import Student
    
    # Get user by ID
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    # Check if user is already suspended
    if user.is_active == "suspended":
        from app.exceptions import ValidationError
        raise ValidationError("User is already suspended")
    
    # Update user status to suspended
    user.is_active = "suspended"
    db.commit()
    db.refresh(user)
    
    # Log activity
    try:
        log_update_activity(
            db=db,
            user_id=current_user.id if current_user else None,
            entity_type="user",
            entity_id=user_id,
            changes={"is_active": "suspended", "suspension_reason": reason},
            institution_id=current_user.institution_id if current_user else None
        )
    except Exception as e:
        # Don't fail the operation if activity logging fails
        pass
    
    # Send suspension email asynchronously
    try:
        from app.helpers.async_helper import run_async_safe
        # Get tenant/institution name and login URL from tenant domain
        institution_name = None
        login_url = None
        try:
            from app.database.base import get_db_session
            global_db = next(get_db_session())
            try:
                from app.models.tenant import Tenant
                tenant = global_db.query(Tenant).filter(
                    Tenant.database_name == db.bind.url.database
                ).first()
                if tenant:
                    institution_name = tenant.name
                    if tenant.domain:
                        login_url = f"https://{tenant.domain}"
            except Exception as tenant_error:
                logger.warning(f"Error getting tenant info: {tenant_error}")
            finally:
                global_db.close()
        except Exception as db_error:
            logger.warning(f"Error accessing global database: {db_error}")
        
        # Get student info if user is a student
        student = None
        if user.role == "student":
            student = db.query(Student).filter(Student.email == user.email).first()
        
        student_name = None
        if student:
            student_name = f"{student.firstname} {student.lastname}".strip()
        else:
            student_name = f"{user.firstname} {user.lastname}".strip()
        
        # Send suspension email with tracking
        async def send_suspension_email():
            from app.services.email_tracker import EmailTracker
            from app.conf.config import settings
            
            html_content, text_content = await EmailService._get_student_suspension_email_content(
                student_name=student_name,
                student_email=user.email,
                student_id=student.student_id if student else str(user.id),
                reason=reason,
                institution_name=institution_name,
                login_url=login_url
            )
            subject = f"{settings.APP_NAME} - Account Suspension Notice"
            
            institution_id = user.institution_id
            
            await EmailTracker.send_with_tracking(
                db=db,
                sender_email=settings.SMTP_FROM_EMAIL,
                recipient_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                institution_id=institution_id
            )
        
        run_async_safe(send_suspension_email())
    except Exception as e:
        # Don't fail suspension if email sending fails
        logger.error(f"Error sending suspension email to user {user.email}: {e}")
    
    return user

def suspend_user_by_student_id(db: Session, student_id: int, reason: str, current_user: Optional[User] = None) -> User:
    """Suspend a student account by student_id (creates user account if it doesn't exist)"""
    from app.models.student import Student
    
    # Get student by ID
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.deleted_at.is_(None)
    ).first()
    
    if not student:
        raise NotFoundError(f"Student with ID {student_id} not found")
    
    # Check if user account already exists for this student (by email)
    existing_user = get_user_by_email(db, student.email)
    
    if existing_user:
        # User account exists, suspend it
        if existing_user.is_active == "suspended":
            from app.exceptions import ValidationError
            raise ValidationError("User is already suspended")
        
        existing_user.is_active = "suspended"
        db.commit()
        db.refresh(existing_user)
        user_to_suspend = existing_user
    else:
        # No user account exists, create one with suspended status
        if not current_user or not current_user.institution_id:
            raise ValidationError("institution_id is required to create user account")
        
        # Generate username
        username = student.student_id or student.email.split('@')[0]
        
        # Check if username already exists
        if get_user_by_username(db, username):
            username = f"{username}_{student.id}"
        
        # Create new user account with suspended status
        new_user = User(
            institution_id=current_user.institution_id,
            firstname=student.firstname,
            middlename=student.middlename,
            lastname=student.lastname,
            gender=student.gender,
            address=student.address,
            email=student.email,
            phone=student.phone,
            username=username,
            password=hash_password("TEMP_PASSWORD_" + str(student.id)),  # Temporary password, user will need to reset
            role="student",
            user_type="TENANT",
            is_active="suspended",  # Create as suspended
            must_change_password="true"
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user_to_suspend = new_user
    
    # Log activity
    try:
        log_update_activity(
            db=db,
            user_id=current_user.id if current_user else None,
            entity_type="user",
            entity_id=user_to_suspend.id,
            changes={"is_active": "suspended", "suspension_reason": reason},
            institution_id=current_user.institution_id if current_user else None
        )
    except Exception as e:
        # Don't fail the operation if activity logging fails
        pass
    
    # Send suspension email asynchronously
    try:
        from app.helpers.async_helper import run_async_safe
        # Get tenant/institution name and login URL from tenant domain
        institution_name = None
        login_url = None
        try:
            from app.database.base import get_db_session
            global_db = next(get_db_session())
            try:
                from app.models.tenant import Tenant
                tenant = global_db.query(Tenant).filter(
                    Tenant.database_name == db.bind.url.database
                ).first()
                if tenant:
                    institution_name = tenant.name
                    if tenant.domain:
                        login_url = f"https://{tenant.domain}"
            except Exception as tenant_error:
                logger.warning(f"Error getting tenant info: {tenant_error}")
            finally:
                global_db.close()
        except Exception as db_error:
            logger.warning(f"Error accessing global database: {db_error}")
        
        student_name = f"{student.firstname} {student.lastname}".strip()
        
        # Send suspension email with tracking
        async def send_suspension_email():
            from app.services.email_tracker import EmailTracker
            from app.conf.config import settings
            
            html_content, text_content = await EmailService._get_student_suspension_email_content(
                student_name=student_name,
                student_email=student.email,
                student_id=student.student_id or str(student.id),
                reason=reason,
                institution_name=institution_name,
                login_url=login_url
            )
            subject = f"{settings.APP_NAME} - Account Suspension Notice"
            
            institution_id = current_user.institution_id if current_user else None
            
            await EmailTracker.send_with_tracking(
                db=db,
                sender_email=settings.SMTP_FROM_EMAIL,
                recipient_email=student.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                institution_id=institution_id
            )
        
        run_async_safe(send_suspension_email())
    except Exception as e:
        # Don't fail suspension if email sending fails
        logger.error(f"Error sending suspension email to student {student.email}: {e}")
    
    return user_to_suspend
