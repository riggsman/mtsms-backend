from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
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
from app.models.note import Note
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
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to view notes"
            )
    
    skip = (page - 1) * page_size
    notes, total = get_notes(
        db=db,
        institution_id=institution_id,
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

@note_router.get("/notes/student/{student_id}", response_model=PaginatedResponse[NoteResponse])
def get_student_notes(
    student_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get notes for courses that a student is enrolled in.
    This endpoint filters notes to only return those for courses the student is actively enrolled in.
    Students can only view their own notes.
    """
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to view notes"
            )
    
    # Import enrollment model
    from app.models.enrollment import Enrollment
    from app.models.student import Student
    
    # Students can only view their own notes
    if current_user.role == UserRole.STUDENT.value:
        # Find student by user email
        student = db.query(Student).filter(
            Student.email == current_user.email,
            Student.institution_id == institution_id,
            Student.deleted_at.is_(None)
        ).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student record not found for this user"
            )
        # Verify the student_id matches the current user's student record
        if str(student.id) != str(student_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students can only view their own notes"
            )
    else:
        # Verify student exists and belongs to the same institution (for admin/staff)
        student = db.query(Student).filter(
            Student.id == student_id,
            Student.institution_id == institution_id,
            Student.deleted_at.is_(None)
        ).first()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with ID {student_id} not found"
            )
    
    # Get all active enrollments for this student
    enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.institution_id == institution_id,
        Enrollment.deleted_at.is_(None),
        Enrollment.status == 'active'  # Only active enrollments
    ).all()
    
    # Extract course IDs from enrollments
    enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]
    
    if not enrolled_course_ids:
        # Return empty result if student has no enrollments
        return PaginatedResponse.create(
            items=[],
            total=0,
            page=page,
            page_size=page_size
        )
    
    # Get notes for enrolled courses
    from app.helpers.pagination import paginate_query
    query = db.query(Note).filter(
        Note.institution_id == institution_id,
        Note.deleted_at.is_(None),
        Note.course_id.in_(enrolled_course_ids)
    )
    
    query = query.order_by(Note.created_at.desc())
    notes, total = paginate_query(query, page=page, page_size=page_size)
    
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
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to view notes"
            )
    
    note = get_note(db, note_id, institution_id)
    
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """
    Create a new note (admin/staff only).
    Supports BOTH:
    - application/json (frontend `noteAPI.create`)
    - multipart/form-data (frontend `noteAPI.createWithFiles`)
    """
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to create notes"
            )

    content_type = (request.headers.get("content-type") or "").lower()

    # Parse input from JSON or multipart/form-data
    pdf_file = None
    word_file = None
    if "application/json" in content_type:
        payload = await request.json()
        try:
            note_data = NoteCreate(**payload)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {e}")
        title = note_data.title
        course_id = note_data.course_id
        department_id = note_data.department_id
        course_code = note_data.course_code
        lecturer_id = note_data.lecturer_id
        content = note_data.content
    else:
        form = await request.form()
        title = form.get("title")
        course_id = form.get("course_id")
        department_id = form.get("department_id")
        course_code = form.get("course_code")
        lecturer_id = form.get("lecturer_id")
        content = form.get("content")
        pdf_file = form.get("pdf_file")
        word_file = form.get("word_file")

        # Basic required field validation for form payload
        if not title or not course_id or not department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: title, course_id, department_id"
            )
        try:
            course_id = int(course_id)
            department_id = int(department_id)
            if lecturer_id is not None and str(lecturer_id).strip() != "":
                lecturer_id = int(lecturer_id)
            else:
                lecturer_id = None
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="course_id, department_id, and lecturer_id (if provided) must be valid integers"
            )

        if content is None:
            content = ""

        note_data = NoteCreate(
            title=str(title).strip(),
            course_id=course_id,
            department_id=department_id,
            course_code=str(course_code).strip() if course_code else None,
            lecturer_id=lecturer_id,
            content=str(content)
        )

    # Validation: Either content or at least one file must be provided
    if (not note_data.content or not str(note_data.content).strip()) and not pdf_file and not word_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide either note content or upload at least one file (PDF or Word)"
        )

    # Determine lecturer_id (admins may specify; staff is auto-derived)
    final_lecturer_id: Optional[int] = None
    if note_data.lecturer_id:
        final_lecturer_id = int(note_data.lecturer_id)
        lecturer = db.query(Teacher).filter(
            Teacher.id == final_lecturer_id,
            Teacher.institution_id == institution_id,
            Teacher.deleted_at.is_(None)
        ).first()
        if not lecturer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lecturer with ID {final_lecturer_id} not found or does not belong to your institution"
            )
    else:
        lecturer = get_teacher_by_user_id(db, current_user.id)
        if lecturer:
            final_lecturer_id = lecturer.id
        elif current_user.role in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a staff member for this note."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only staff members can create notes. Please ensure your account is linked to a staff/teacher profile."
            )

    # Create note: with files if present, else JSON/text note creation
    if pdf_file or word_file:
        note = await create_note_with_files(
            db=db,
            title=note_data.title,
            course_id=note_data.course_id,
            department_id=note_data.department_id,
            course_code=note_data.course_code,
            lecturer_id=final_lecturer_id,
            content=note_data.content or "",
            pdf_file=pdf_file,
            word_file=word_file,
            institution_id=institution_id,
            current_user=current_user
        )
    else:
        note = create_note(
            db=db,
            note=NoteCreate(
                title=note_data.title,
                course_id=note_data.course_id,
                department_id=note_data.department_id,
                course_code=note_data.course_code,
                lecturer_id=final_lecturer_id,
                content=note_data.content
            ),
            institution_id=institution_id,
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
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """Generate PDF and/or Word files for a note"""
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution"
            )
    
    note = get_note(db, note_id, institution_id)
    
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
            institution_id=institution_id,
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """
    Update a note (admin/staff only).
    Supports BOTH:
    - application/json (frontend `noteAPI.update`)
    - multipart/form-data (frontend `noteAPI.updateWithFiles`)
    """
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to update notes"
            )
    
    # Get existing note
    note = get_note(db, note_id, institution_id)

    content_type = (request.headers.get("content-type") or "").lower()
    pdf_file = None
    word_file = None
    if "application/json" in content_type:
        payload = await request.json()
        try:
            note_update = NoteUpdate(**payload)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {e}")

        note = update_note(
            db=db,
            note_id=note_id,
            note_update=note_update,
            institution_id=institution_id,
            current_user=current_user
        )
    else:
        form = await request.form()
        title = form.get("title")
        course_id = form.get("course_id")
        department_id = form.get("department_id")
        course_code = form.get("course_code")
        content = form.get("content")
        pdf_file = form.get("pdf_file")
        word_file = form.get("word_file")

        # Convert ints where provided
        try:
            course_id = int(course_id) if course_id is not None and str(course_id).strip() != "" else None
            department_id = int(department_id) if department_id is not None and str(department_id).strip() != "" else None
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="course_id and department_id must be valid integers when provided"
            )

        if pdf_file or word_file:
            note = await update_note_with_files(
                db=db,
                note_id=note_id,
                title=str(title).strip() if title is not None else None,
                course_id=course_id,
                department_id=department_id,
                course_code=str(course_code).strip() if course_code is not None else None,
                content=str(content) if content is not None else None,
                pdf_file=pdf_file,
                word_file=word_file,
                institution_id=institution_id,
                current_user=current_user
            )
        else:
            note_update = NoteUpdate(
                title=str(title).strip() if title is not None else None,
                course_id=course_id,
                department_id=department_id,
                course_code=str(course_code).strip() if course_code is not None else None,
                content=str(content) if content is not None else None
            )
            note = update_note(
                db=db,
                note_id=note_id,
                note_update=note_update,
                institution_id=institution_id,
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
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """Delete a note (admin/staff only)"""
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to delete notes"
            )
    
    delete_note(
        db=db,
        note_id=note_id,
        institution_id=institution_id,
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
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution"
            )
    
    note = get_note(db, note_id, institution_id)
    
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
