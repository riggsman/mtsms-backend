from fastapi import APIRouter, Depends, Query, HTTPException, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.note import NoteCreate, NoteUpdate, NoteResponse
from app.apis.notes import (
    create_note,
    get_note,
    get_notes,
    update_note,
    delete_note,
    update_note_file_paths,
    create_note_with_files,
    update_note_with_files
)
from app.apis.teachers import get_teacher_by_user_id
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse
from app.helpers.file_generator import generate_pdf, generate_word
from app.models.course import Course
from app.models.teacher import Teacher
import os

note_router = APIRouter()

@note_router.get("/notes", response_model=PaginatedResponse[NoteResponse])
def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    course_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    lecturer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of notes for the current tenant (any authenticated tenant user)"""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to view notes"
        )
    
    skip = (page - 1) * page_size
    notes, total = get_notes(
        db=db,
        institution_id=current_user.institution_id,
        skip=skip,
        limit=page_size,
        course_id=course_id,
        department_id=department_id,
        lecturer_id=lecturer_id
    )
    
    # Enrich notes with related data
    enriched_notes = []
    for note in notes:
        note_dict = {
            'id': note.id,
            'institution_id': note.institution_id,
            'title': note.title,
            'course_id': note.course_id,
            'course_code': note.course_code,
            'department_id': note.department_id,
            'lecturer_id': note.lecturer_id,
            'content': note.content,
            'pdf_file_path': note.pdf_file_path,
            'word_file_path': note.word_file_path,
            'created_by': note.created_by,
            'created_at': note.created_at,
            'updated_at': note.updated_at
        }
        
        # Get course name
        course = db.query(Course).filter(Course.id == note.course_id).first()
        if course:
            note_dict['course_name'] = course.name
            note_dict['course_code_full'] = course.code
        
        # Get department name
        from app.models.department import Department
        dept = db.query(Department).filter(Department.id == note.department_id).first()
        if dept:
            note_dict['department_name'] = dept.name
        
        # Get lecturer name
        lecturer = db.query(Teacher).filter(Teacher.id == note.lecturer_id).first()
        if lecturer:
            note_dict['lecturer_name'] = f"{lecturer.firstname} {lecturer.lastname}"
        
        enriched_notes.append(NoteResponse(**note_dict))
    
    return PaginatedResponse.create(
        items=enriched_notes,
        total=total,
        page=page,
        page_size=page_size
    )

@note_router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note_endpoint(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a note by ID (tenant-scoped)"""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to view notes"
        )
    
    note = get_note(db, note_id, current_user.institution_id)
    
    # Enrich with related data
    note_dict = {
        'id': note.id,
        'institution_id': note.institution_id,
        'title': note.title,
        'course_id': note.course_id,
        'course_code': note.course_code,
        'department_id': note.department_id,
        'lecturer_id': note.lecturer_id,
        'content': note.content,
        'pdf_file_path': note.pdf_file_path,
        'word_file_path': note.word_file_path,
        'created_by': note.created_by,
        'created_at': note.created_at,
        'updated_at': note.updated_at
    }
    
    # Get course name
    course = db.query(Course).filter(Course.id == note.course_id).first()
    if course:
        note_dict['course_name'] = course.name
        note_dict['course_code_full'] = course.code
    
    # Get department name
    from app.models.department import Department
    dept = db.query(Department).filter(Department.id == note.department_id).first()
    if dept:
        note_dict['department_name'] = dept.name
    
    # Get lecturer name
    lecturer = db.query(Teacher).filter(Teacher.id == note.lecturer_id).first()
    if lecturer:
        note_dict['lecturer_name'] = f"{lecturer.firstname} {lecturer.lastname}"
    
    return NoteResponse(**note_dict)

@note_router.post("/notes", response_model=NoteResponse, status_code=201)
async def create_note_endpoint(
    title: str = Form(...),
    course_id: int = Form(...),
    department_id: int = Form(...),
    course_code: Optional[str] = Form(None),
    lecturer_id: Optional[int] = Form(None),
    content: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    word_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new note (staff/admin only). Supports both text content and file uploads."""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to create notes"
        )
    
    # Validation: Either content or at least one file must be provided
    if not content and not pdf_file and not word_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide either note content or upload at least one file (PDF or Word)"
        )
    
    # Determine lecturer_id
    final_lecturer_id = None
    
    # If lecturer_id is provided in request, use it (for admins)
    if lecturer_id:
        final_lecturer_id = lecturer_id
        # Verify the lecturer exists and belongs to the institution
        lecturer = db.query(Teacher).filter(
            Teacher.id == lecturer_id,
            Teacher.institution_id == current_user.institution_id,
            Teacher.deleted_at.is_(None)
        ).first()
        if not lecturer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lecturer with ID {lecturer_id} not found or does not belong to your institution"
            )
    else:
        # For staff members, try to get lecturer_id from their linked teacher profile
        lecturer = get_teacher_by_user_id(db, current_user.id)
        if lecturer:
            final_lecturer_id = lecturer.id
        elif current_user.role in ["admin", "super_admin"]:
            # Admins must specify which staff member this note belongs to
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a staff member for this note."
            )
        else:
            # Staff members must be linked to a teacher profile
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only staff members can create notes. Please ensure your account is linked to a staff/teacher profile."
            )
    
    # If files are provided, use file upload endpoint
    if pdf_file or word_file:
        note = await create_note_with_files(
            db=db,
            title=title,
            course_id=course_id,
            department_id=department_id,
            course_code=course_code,
            lecturer_id=final_lecturer_id,
            content=content or '',
            pdf_file=pdf_file,
            word_file=word_file,
            institution_id=current_user.institution_id,
            current_user=current_user
        )
    else:
        # Use regular text-based note creation
        note_data = NoteCreate(
            title=title,
            course_id=course_id,
            department_id=department_id,
            course_code=course_code,
            lecturer_id=final_lecturer_id,
            content=content or ''
        )
        note = create_note(
            db=db,
            note=note_data,
            institution_id=current_user.institution_id,
            current_user=current_user
        )
    
    # Enrich with related data for response
    note_dict = {
        'id': note.id,
        'institution_id': note.institution_id,
        'title': note.title,
        'course_id': note.course_id,
        'course_code': note.course_code,
        'department_id': note.department_id,
        'lecturer_id': note.lecturer_id,
        'content': note.content,
        'pdf_file_path': note.pdf_file_path,
        'word_file_path': note.word_file_path,
        'created_by': note.created_by,
        'created_at': note.created_at,
        'updated_at': note.updated_at
    }
    
    # Get course name
    course = db.query(Course).filter(Course.id == note.course_id).first()
    if course:
        note_dict['course_name'] = course.name
        note_dict['course_code_full'] = course.code
    
    # Get department name
    from app.models.department import Department
    dept = db.query(Department).filter(Department.id == note.department_id).first()
    if dept:
        note_dict['department_name'] = dept.name
    
    # Get lecturer name
    lecturer_obj = db.query(Teacher).filter(Teacher.id == note.lecturer_id).first()
    if lecturer_obj:
        note_dict['lecturer_name'] = f"{lecturer_obj.firstname} {lecturer_obj.lastname}"
    
    return NoteResponse(**note_dict)

@note_router.post("/notes/{note_id}/generate-files", response_model=NoteResponse)
def generate_note_files(
    note_id: int,
    format_type: str = Query(..., pattern="^(pdf|word|both)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Generate PDF and/or Word files for a note"""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    note = get_note(db, note_id, current_user.institution_id)
    
    # Get related data
    course = db.query(Course).filter(Course.id == note.course_id).first()
    lecturer = db.query(Teacher).filter(Teacher.id == note.lecturer_id).first()
    
    course_name = course.name if course else "Unknown Course"
    course_code = note.course_code or (course.code if course else None)
    lecturer_name = f"{lecturer.firstname} {lecturer.lastname}" if lecturer else None
    
    # Generate files
    pdf_path = None
    word_path = None
    
    if format_type in ['pdf', 'both']:
        pdf_path = generate_pdf(
            title=note.title,
            course_name=course_name,
            course_code=course_code,
            content=note.content,
            lecturer_name=lecturer_name
        )
    
    if format_type in ['word', 'both']:
        word_path = generate_word(
            title=note.title,
            course_name=course_name,
            course_code=course_code,
            content=note.content,
            lecturer_name=lecturer_name
        )
    
    # Update note with file paths
    if pdf_path or word_path:
        note = update_note_file_paths(
            db=db,
            note_id=note_id,
            institution_id=current_user.institution_id,
            pdf_path=pdf_path,
            word_path=word_path
        )
    
    # Return enriched response
    note_dict = {
        'id': note.id,
        'institution_id': note.institution_id,
        'title': note.title,
        'course_id': note.course_id,
        'course_code': note.course_code,
        'department_id': note.department_id,
        'lecturer_id': note.lecturer_id,
        'content': note.content,
        'pdf_file_path': note.pdf_file_path,
        'word_file_path': note.word_file_path,
        'created_by': note.created_by,
        'created_at': note.created_at,
        'updated_at': note.updated_at
    }
    
    if course:
        note_dict['course_name'] = course.name
        note_dict['course_code_full'] = course.code
    
    from app.models.department import Department
    dept = db.query(Department).filter(Department.id == note.department_id).first()
    if dept:
        note_dict['department_name'] = dept.name
    
    if lecturer:
        note_dict['lecturer_name'] = f"{lecturer.firstname} {lecturer.lastname}"
    
    return NoteResponse(**note_dict)

@note_router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note_endpoint(
    note_id: int,
    title: Optional[str] = Form(None),
    course_id: Optional[int] = Form(None),
    department_id: Optional[int] = Form(None),
    course_code: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    word_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a note (staff/admin only). Supports both text content and file uploads."""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to update notes"
        )
    
    # Get existing note
    note = get_note(db, note_id, current_user.institution_id)
    
    # If files are provided, use file upload endpoint
    if pdf_file or word_file:
        note = await update_note_with_files(
            db=db,
            note_id=note_id,
            title=title,
            course_id=course_id,
            department_id=department_id,
            course_code=course_code,
            content=content,
            pdf_file=pdf_file,
            word_file=word_file,
            institution_id=current_user.institution_id,
            current_user=current_user
        )
    else:
        # Use regular text-based note update
        note_update = NoteUpdate(
            title=title,
            course_id=course_id,
            department_id=department_id,
            course_code=course_code,
            content=content
        )
        note = update_note(
            db=db,
            note_id=note_id,
            note_update=note_update,
            institution_id=current_user.institution_id,
            current_user=current_user
        )
    
    # Enrich with related data
    note_dict = {
        'id': note.id,
        'institution_id': note.institution_id,
        'title': note.title,
        'course_id': note.course_id,
        'course_code': note.course_code,
        'department_id': note.department_id,
        'lecturer_id': note.lecturer_id,
        'content': note.content,
        'pdf_file_path': note.pdf_file_path,
        'word_file_path': note.word_file_path,
        'created_by': note.created_by,
        'created_at': note.created_at,
        'updated_at': note.updated_at
    }
    
    course = db.query(Course).filter(Course.id == note.course_id).first()
    if course:
        note_dict['course_name'] = course.name
        note_dict['course_code_full'] = course.code
    
    from app.models.department import Department
    dept = db.query(Department).filter(Department.id == note.department_id).first()
    if dept:
        note_dict['department_name'] = dept.name
    
    lecturer = db.query(Teacher).filter(Teacher.id == note.lecturer_id).first()
    if lecturer:
        note_dict['lecturer_name'] = f"{lecturer.firstname} {lecturer.lastname}"
    
    return NoteResponse(**note_dict)

@note_router.delete("/notes/{note_id}", status_code=204)
def delete_note_endpoint(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a note (staff/admin only)"""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to delete notes"
        )
    
    delete_note(
        db=db,
        note_id=note_id,
        institution_id=current_user.institution_id,
        current_user=current_user
    )
    return None

@note_router.get("/notes/{note_id}/download/{file_type}")
def download_note_file(
    note_id: int,
    file_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Download a note file (PDF or Word)"""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    note = get_note(db, note_id, current_user.institution_id)
    
    file_path = None
    content_type = None
    filename = None
    
    if file_type == 'pdf' and note.pdf_file_path:
        file_path = note.pdf_file_path
        content_type = 'application/pdf'
        filename = f"{note.title.replace(' ', '_')}.pdf"
    elif file_type == 'word' and note.word_file_path:
        file_path = note.word_file_path
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        filename = f"{note.title.replace(' ', '_')}.docx"
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{file_type.upper()} file not found for this note"
        )
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename
    )
