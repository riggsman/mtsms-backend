from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from app.models.note import Note
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.department import Department
from app.models.user import User
from app.schemas.note import NoteCreate, NoteUpdate, NoteResponse
from app.exceptions import NotFoundError, ValidationError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity
from app.helpers.file_generator import generate_pdf, generate_word
from app.helpers.file_upload import save_uploaded_file, delete_file
import os
import datetime
import re

def create_note(
    db: Session,
    note: NoteCreate,
    institution_id: int,
    lecturer_id: Optional[int] = None,
    current_user: Optional[User] = None
) -> Note:
    """Create a new note"""
    if not institution_id:
        raise ValidationError("institution_id is required to create a note")
    
    # Verify course exists and belongs to institution
    course = db.query(Course).filter(
        Course.id == note.course_id,
        Course.institution_id == institution_id,
        Course.deleted_at.is_(None)
    ).first()
    if not course:
        raise NotFoundError(f"Course with ID {note.course_id} not found")
    
    # Use lecturer_id from note if provided, otherwise use the passed lecturer_id
    final_lecturer_id = note.lecturer_id if note.lecturer_id else lecturer_id
    if not final_lecturer_id:
        raise ValidationError("lecturer_id is required to create a note")
    
    # Verify lecturer exists and belongs to institution
    lecturer = db.query(Teacher).filter(
        Teacher.id == final_lecturer_id,
        Teacher.institution_id == institution_id,
        Teacher.deleted_at.is_(None)
    ).first()
    if not lecturer:
        raise NotFoundError(f"Lecturer with ID {final_lecturer_id} not found")
    
    # Create note
    new_note = Note(
        institution_id=institution_id,
        title=note.title,
        course_id=note.course_id,
        course_code=note.course_code or course.code,
        department_id=note.department_id,
        lecturer_id=final_lecturer_id,
        content=note.content,
        created_by=current_user.id if current_user else None
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    
    # Automatically generate PDF and Word files
    try:
        lecturer_name = f"{lecturer.firstname} {lecturer.lastname}" if lecturer else None
        course_code = note.course_code or course.code
        
        # Generate PDF
        pdf_path = generate_pdf(
            title=note.title,
            course_name=course.name,
            course_code=course_code,
            content=note.content,
            lecturer_name=lecturer_name
        )
        
        # Generate Word
        word_path = generate_word(
            title=note.title,
            course_name=course.name,
            course_code=course_code,
            content=note.content,
            lecturer_name=lecturer_name
        )
        
        # Update note with file paths
        if pdf_path:
            new_note.pdf_file_path = pdf_path
        if word_path:
            new_note.word_file_path = word_path
        
        if pdf_path or word_path:
            db.commit()
            db.refresh(new_note)
    except Exception as e:
        print(f"Error generating files for note: {e}")
        # Continue even if file generation fails
    
    # Log activity
    try:
        log_create_activity(
            db=db,
            current_user=current_user,
            entity_type="note",
            entity_id=new_note.id,
            entity_name=note.title,
            institution_id=institution_id,
            content=f"Created note: {note.title} for course {course.code}"
        )
    except Exception as e:
        print(f"Error logging note creation activity: {e}")
    
    return new_note

def get_note(db: Session, note_id: int, institution_id: int) -> Note:
    """Get a note by ID (tenant-scoped)"""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.institution_id == institution_id,
        Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise NotFoundError(f"Note with ID {note_id} not found")
    return note

def get_notes(
    db: Session,
    institution_id: int,
    skip: int = 0,
    limit: int = 100,
    course_id: Optional[int] = None,
    department_id: Optional[int] = None,
    lecturer_id: Optional[int] = None
) -> tuple[List[Note], int]:
    """Get list of notes with pagination and filters"""
    query = db.query(Note).filter(
        Note.institution_id == institution_id,
        Note.deleted_at.is_(None)
    )
    
    if course_id:
        query = query.filter(Note.course_id == course_id)
    if department_id:
        query = query.filter(Note.department_id == department_id)
    if lecturer_id:
        query = query.filter(Note.lecturer_id == lecturer_id)
    
    query = query.order_by(Note.created_at.desc())
    notes, total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    return notes, total

def update_note(
    db: Session,
    note_id: int,
    note_update: NoteUpdate,
    institution_id: int,
    current_user: User
) -> Note:
    """Update a note (tenant-scoped)"""
    note = get_note(db, note_id, institution_id)
    
    update_data = note_update.dict(exclude_unset=True)
    
    # If course_id is being updated, verify it exists
    if "course_id" in update_data:
        course = db.query(Course).filter(
            Course.id == update_data["course_id"],
            Course.institution_id == institution_id,
            Course.deleted_at.is_(None)
        ).first()
        if not course:
            raise NotFoundError(f"Course with ID {update_data['course_id']} not found")
    
    # Check if content, title, or course was updated (need to regenerate files)
    content_updated = "content" in update_data
    title_updated = "title" in update_data
    course_updated = "course_id" in update_data
    
    for field, value in update_data.items():
        setattr(note, field, value)
    
    db.commit()
    db.refresh(note)
    
    # Regenerate files if content, title, or course was updated
    if content_updated or title_updated or course_updated:
        try:
            # Get updated course info
            updated_course = db.query(Course).filter(Course.id == note.course_id).first()
            course_name = updated_course.name if updated_course else "Unknown Course"
            course_code = note.course_code or (updated_course.code if updated_course else None)
            
            # Get lecturer info
            lecturer = db.query(Teacher).filter(Teacher.id == note.lecturer_id).first()
            lecturer_name = f"{lecturer.firstname} {lecturer.lastname}" if lecturer else None
            
            # Generate PDF
            pdf_path = generate_pdf(
                title=note.title,
                course_name=course_name,
                course_code=course_code,
                content=note.content,
                lecturer_name=lecturer_name
            )
            
            # Generate Word
            word_path = generate_word(
                title=note.title,
                course_name=course_name,
                course_code=course_code,
                content=note.content,
                lecturer_name=lecturer_name
            )
            
            # Update note with new file paths
            if pdf_path:
                note.pdf_file_path = pdf_path
            if word_path:
                note.word_file_path = word_path
            
            if pdf_path or word_path:
                db.commit()
                db.refresh(note)
        except Exception as e:
            print(f"Error regenerating files for note: {e}")
            # Continue even if file generation fails
    
    # Log activity
    try:
        log_update_activity(
            db=db,
            current_user=current_user,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
            institution_id=institution_id,
            content=f"Updated note: {note.title}"
        )
    except Exception as e:
        print(f"Error logging note update activity: {e}")
    
    return note

def delete_note(
    db: Session,
    note_id: int,
    institution_id: int,
    current_user: User
) -> bool:
    """Soft delete a note (tenant-scoped)"""
    note = get_note(db, note_id, institution_id)
    note_name = note.title
    
    note.deleted_at = datetime.datetime.utcnow()
    db.commit()
    
    # Log activity
    try:
        log_delete_activity(
            db=db,
            current_user=current_user,
            entity_type="note",
            entity_id=note_id,
            entity_name=note_name,
            institution_id=institution_id,
            content=f"Deleted note: {note_name}"
        )
    except Exception as e:
        print(f"Error logging note deletion activity: {e}")
    
    return True

def update_note_file_paths(
    db: Session,
    note_id: int,
    institution_id: int,
    pdf_path: Optional[str] = None,
    word_path: Optional[str] = None
) -> Note:
    """Update file paths for a note"""
    note = get_note(db, note_id, institution_id)
    
    if pdf_path:
        note.pdf_file_path = pdf_path
    if word_path:
        note.word_file_path = word_path
    
    db.commit()
    db.refresh(note)
    return note


async def create_note_with_files(
    db: Session,
    title: str,
    course_id: int,
    department_id: int,
    lecturer_id: int,
    institution_id: int,
    course_code: Optional[str] = None,
    content: Optional[str] = None,
    pdf_file: Optional[UploadFile] = None,
    word_file: Optional[UploadFile] = None,
    current_user: Optional[User] = None
) -> Note:
    """Create a note with uploaded files"""
    # Verify course exists
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.institution_id == institution_id,
        Course.deleted_at.is_(None)
    ).first()
    if not course:
        raise NotFoundError(f"Course with ID {course_id} not found")
    
    # Verify lecturer exists
    lecturer = db.query(Teacher).filter(
        Teacher.id == lecturer_id,
        Teacher.institution_id == institution_id,
        Teacher.deleted_at.is_(None)
    ).first()
    if not lecturer:
        raise NotFoundError(f"Lecturer with ID {lecturer_id} not found")
    
    # Get tenant domain for file naming
    from app.database.base import get_db_session
    global_db = next(get_db_session())
    try:
        from app.models.tenant import Tenant
        tenant = global_db.query(Tenant).filter(
            Tenant.database_name == db.bind.url.database
        ).first()
        tenant_domain = tenant.domain if tenant else "default"
    except:
        tenant_domain = "default"
    finally:
        global_db.close()
    
    # Save uploaded files
    pdf_path = None
    word_path = None
    
    if pdf_file:
        try:
            # Validate PDF file
            if pdf_file.content_type not in ['application/pdf']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF file must be of type application/pdf"
                )
            
            # Validate file size (10MB max)
            if pdf_file.size and pdf_file.size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF file size exceeds 10MB limit"
                )
            
            # Use note title as filename (sanitize it)
            sanitized_title = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', title)
            sanitized_title = re.sub(r'_+', '_', sanitized_title).strip('_')
            
            file_path, relative_path = await save_uploaded_file(
                file=pdf_file,
                tenant_domain=tenant_domain,
                file_category='notes',
                subdirectory='notes',
                custom_filename=sanitized_title
            )
            pdf_path = relative_path
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save PDF file: {str(e)}"
            )
    
    if word_file:
        try:
            # Validate Word file
            allowed_word_types = [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
            if word_file.content_type not in allowed_word_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Word file must be .doc or .docx format"
                )
            
            # Validate file size (10MB max)
            if word_file.size and word_file.size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Word file size exceeds 10MB limit"
                )
            
            # Use note title as filename (sanitize it)
            sanitized_title = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', title)
            sanitized_title = re.sub(r'_+', '_', sanitized_title).strip('_')
            
            file_path, relative_path = await save_uploaded_file(
                file=word_file,
                tenant_domain=tenant_domain,
                file_category='notes',
                subdirectory='notes',
                custom_filename=sanitized_title
            )
            word_path = relative_path
        except HTTPException:
            raise
        except Exception as e:
            # Clean up PDF if it was saved
            if pdf_path:
                delete_file(pdf_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save Word file: {str(e)}"
            )
    
    # Create note
    new_note = Note(
        institution_id=institution_id,
        title=title,
        course_id=course_id,
        course_code=course_code or course.code,
        department_id=department_id,
        lecturer_id=lecturer_id,
        content=content or '',
        pdf_file_path=pdf_path,
        word_file_path=word_path,
        created_by=current_user.id if current_user else None
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    
    # Log activity
    try:
        log_create_activity(
            db=db,
            current_user=current_user,
            entity_type="note",
            entity_id=new_note.id,
            entity_name=title,
            institution_id=institution_id,
            content=f"Created note: {title} for course {course.code}"
        )
    except Exception as e:
        print(f"Error logging note creation activity: {e}")
    
    return new_note


async def update_note_with_files(
    db: Session,
    note_id: int,
    institution_id: int,
    title: Optional[str] = None,
    course_id: Optional[int] = None,
    department_id: Optional[int] = None,
    course_code: Optional[str] = None,
    content: Optional[str] = None,
    pdf_file: Optional[UploadFile] = None,
    word_file: Optional[UploadFile] = None,
    current_user: Optional[User] = None
) -> Note:
    """Update a note with uploaded files"""
    note = get_note(db, note_id, institution_id)
    
    # Get tenant domain for file naming
    from app.database.base import get_db_session
    global_db = next(get_db_session())
    try:
        from app.models.tenant import Tenant
        tenant = global_db.query(Tenant).filter(
            Tenant.database_name == db.bind.url.database
        ).first()
        tenant_domain = tenant.domain if tenant else "default"
    except:
        tenant_domain = "default"
    finally:
        global_db.close()
    
    # Update basic fields
    if title is not None:
        note.title = title
    if course_id is not None:
        # Verify course exists
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.institution_id == institution_id,
            Course.deleted_at.is_(None)
        ).first()
        if not course:
            raise NotFoundError(f"Course with ID {course_id} not found")
        note.course_id = course_id
    if department_id is not None:
        note.department_id = department_id
    if course_code is not None:
        note.course_code = course_code
    if content is not None:
        note.content = content
    
    # Handle file uploads
    if pdf_file:
        # Delete old PDF if exists
        if note.pdf_file_path:
            delete_file(note.pdf_file_path)
        
        try:
            # Validate PDF file
            if pdf_file.content_type not in ['application/pdf']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF file must be of type application/pdf"
                )
            
            # Validate file size (10MB max)
            if pdf_file.size and pdf_file.size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF file size exceeds 10MB limit"
                )
            
            # Use note title as filename (use current title or updated title)
            note_title = title if title is not None else note.title
            sanitized_title = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', note_title)
            sanitized_title = re.sub(r'_+', '_', sanitized_title).strip('_')
            
            file_path, relative_path = await save_uploaded_file(
                file=pdf_file,
                tenant_domain=tenant_domain,
                file_category='notes',
                subdirectory='notes',
                custom_filename=sanitized_title
            )
            note.pdf_file_path = relative_path
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save PDF file: {str(e)}"
            )
    
    if word_file:
        # Delete old Word file if exists
        if note.word_file_path:
            delete_file(note.word_file_path)
        
        try:
            # Validate Word file
            allowed_word_types = [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
            if word_file.content_type not in allowed_word_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Word file must be .doc or .docx format"
                )
            
            # Validate file size (10MB max)
            if word_file.size and word_file.size > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Word file size exceeds 10MB limit"
                )
            
            # Use note title as filename (use current title or updated title)
            note_title = title if title is not None else note.title
            sanitized_title = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', note_title)
            sanitized_title = re.sub(r'_+', '_', sanitized_title).strip('_')
            
            file_path, relative_path = await save_uploaded_file(
                file=word_file,
                tenant_domain=tenant_domain,
                file_category='notes',
                subdirectory='notes',
                custom_filename=sanitized_title
            )
            note.word_file_path = relative_path
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save Word file: {str(e)}"
            )
    
    db.commit()
    db.refresh(note)
    
    # Log activity
    try:
        log_update_activity(
            db=db,
            current_user=current_user,
            entity_type="note",
            entity_id=note.id,
            entity_name=note.title,
            institution_id=institution_id,
            content=f"Updated note: {note.title}"
        )
    except Exception as e:
        print(f"Error logging note update activity: {e}")
    
    return note
