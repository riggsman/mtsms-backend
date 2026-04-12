from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.models.student import Student
from app.exceptions import NotFoundError
import os
from pathlib import Path

try:
    from app.services.certificate import generate_transcript_pdf, generate_result_slip_pdf
    CERTIFICATE_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"[Certificate] Warning: Could not import certificate service: {e}")
    generate_transcript_pdf = None
    generate_result_slip_pdf = None
    CERTIFICATE_SERVICE_AVAILABLE = False

certificate_router = APIRouter()


@certificate_router.api_route("/result-slip", methods=["OPTIONS"])
async def options_result_slip():
    """Handle CORS preflight for result slip endpoint"""
    print("[Certificate] OPTIONS /result-slip")
    return Response(status_code=200)


@certificate_router.api_route("/transcript", methods=["OPTIONS"])
async def options_transcript():
    """Handle CORS preflight for transcript endpoint"""
    print("[Certificate] OPTIONS /transcript")
    return Response(status_code=200)


def check_student_access(current_user: User, student_no: str, db: Session, institution_id: int):
    student = db.query(Student).filter(
        Student.student_id == student_no,
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None)
    ).first()
    
    if not student:
        raise NotFoundError(f"Student with ID {student_no} not found")
    
    is_student_own_record = (
        student.email == current_user.email or
        str(student.id) == str(getattr(current_user, 'student_id', None))
    )
    
    return student, is_student_own_record


@certificate_router.get("/transcript/{student_no}")
def generate_transcript(
    student_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Generate a student transcript (Academic Record).
    
    - **student_no**: The student registration number
    
    Access:
    - Students can only generate their own transcript
    - Admin, Secretary, and Super Admin can generate any transcript
    """
    institution_id = current_user.institution_id
    
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    student, is_own_record = check_student_access(current_user, student_no, db, institution_id)
    
    from app.helpers.user_roles import user_has_role
    is_privileged = user_has_role(current_user, UserRole.ADMIN.value) or \
                   user_has_role(current_user, UserRole.SECRETARY.value) or \
                   user_has_role(current_user, UserRole.SUPER_ADMIN.value) or \
                   user_has_role(current_user, UserRole.STAFF.value)
    
    if not is_own_record and not is_privileged:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only generate your own transcript"
        )
    
    try:
        pdf_buffer = generate_transcript_pdf(
            db=db,
            student_no=student_no,
            institution_id=institution_id
        )
        
        filename = f"transcript_{student_no}_{student.lastname}.pdf"
        
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate transcript: {str(e)}"
        )


@certificate_router.get("/result-slip/{student_no}")
def generate_result_slip(
    student_no: str,
    semester: str = Query(None, description="Semester to generate result slip for (e.g., 'Y1S1')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Generate a student result slip.
    
    - **student_no**: The student registration number
    - **semester**: Optional semester filter (e.g., 'Y1S1', 'Y2S1')
    
    Access:
    - Students can only generate their own result slip
    - Admin, Secretary, and Super Admin can generate any result slip
    """
    institution_id = current_user.institution_id
    
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    student, is_own_record = check_student_access(current_user, student_no, db, institution_id)
    
    from app.helpers.user_roles import user_has_role
    is_privileged = user_has_role(current_user, UserRole.ADMIN.value) or \
                   user_has_role(current_user, UserRole.SECRETARY.value) or \
                   user_has_role(current_user, UserRole.SUPER_ADMIN.value) or \
                   user_has_role(current_user, UserRole.STAFF.value)
    
    if not is_own_record and not is_privileged:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only generate your own result slip"
        )
    
    try:
        pdf_buffer = generate_result_slip_pdf(
            db=db,
            student_no=student_no,
            institution_id=institution_id,
            semester=semester
        )
        
        filename = f"result_slip_{student_no}"
        if semester:
            filename += f"_{semester}"
        filename += ".pdf"
        
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate result slip: {str(e)}"
        )


@certificate_router.get("/certificates/transcript")
def generate_my_transcript(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Generate transcript for the current logged-in student.
    """
    print(f"[Certificate] generate_my_transcript called")
    print(f"[Certificate] Service available: {CERTIFICATE_SERVICE_AVAILABLE}")
    
    if not CERTIFICATE_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate service is not available. Please check server configuration."
        )
    
    print(f"[Certificate] current_user: {current_user.email}, institution_id: {current_user.institution_id}")
    
    institution_id = current_user.institution_id
    
    if not institution_id:
        print("[Certificate] No institution_id found for user")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    student = db.query(Student).filter(
        Student.email == current_user.email,
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None)
    ).first()
    
    print(f"[Certificate] Student lookup by email: {current_user.email}")
    print(f"[Certificate] Student found: {student}")
    
    if not student:
        print(f"[Certificate] No student found with email {current_user.email} and institution_id {institution_id}")
        raise NotFoundError("Student record not found for current user")
    
    try:
        print(f"[Certificate] Generating transcript PDF for student: {student.student_id}")
        pdf_buffer = generate_transcript_pdf(
            db=db,
            student_no=student.student_id,
            institution_id=institution_id
        )
        print(f"[Certificate] Transcript PDF generated successfully")
        
        filename = f"transcript_{student.student_id}_{student.lastname}.pdf"
        
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ValueError as e:
        print(f"[Certificate] ValueError: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        print(f"[Certificate] Exception: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate transcript: {str(e)}"
        )


@certificate_router.get("/certificates/result-slip")
def generate_my_result_slip(
    semester: str = Query(None, description="Semester to generate result slip for (e.g., 'Y1S1')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Generate result slip for the current logged-in student.
    """
    print(f"[Certificate] generate_my_result_slip called")
    print(f"[Certificate] Service available: {CERTIFICATE_SERVICE_AVAILABLE}")
    
    if not CERTIFICATE_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate service is not available. Please check server configuration."
        )
    
    print(f"[Certificate] current_user: {current_user.email}, institution_id: {current_user.institution_id}")
    
    institution_id = current_user.institution_id
    
    if not institution_id:
        print("[Certificate] No institution_id found for user")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    student = db.query(Student).filter(
        Student.email == current_user.email,
        Student.institution_id == institution_id,
        Student.deleted_at.is_(None)
    ).first()
    
    print(f"[Certificate] Student lookup by email: {current_user.email}")
    print(f"[Certificate] Student found: {student}")
    
    if not student:
        print(f"[Certificate] No student found with email {current_user.email} and institution_id {institution_id}")
        raise NotFoundError("Student record not found for current user")
    
    try:
        print(f"[Certificate] Generating PDF for student: {student.student_id}, semester: {semester}")
        pdf_buffer = generate_result_slip_pdf(
            db=db,
            student_no=student.student_id,
            institution_id=institution_id,
            semester=semester
        )
        print(f"[Certificate] PDF generated successfully")
        
        filename = f"result_slip_{student.student_id}"
        if semester:
            filename += f"_{semester}"
        filename += ".pdf"
        
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ValueError as e:
        print(f"[Certificate] ValueError: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        print(f"[Certificate] Exception: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate result slip: {str(e)}"
        )
