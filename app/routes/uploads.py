"""
Routes for handling file uploads (tenant logo and profile pictures)
"""
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, status, Header
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from typing import Optional
from app.apis.uploads import (
    upload_tenant_logo,
    upload_profile_picture,
    delete_profile_picture,
    delete_tenant_logo
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.schemas.tenant_settings import TenantSettingsResponse
from app.schemas.users import UserResponse
import os
from pathlib import Path
from app.helpers.user_roles import user_is_system_admin
from app.helpers.tenant_scope import institution_id_for_user
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.apis.users import get_user
from app.apis.students import resolve_student_for_logged_in_user
from app.models.student_uploaded_document import StudentUploadedDocument
from datetime import datetime

upload_router = APIRouter()
MAX_STUDENT_DOCUMENTS = 5
MAX_STUDENT_DOCUMENT_SIZE_BYTES = 100 * 1024
ID_CARD_SIDES = {"front", "back"}


def _read_and_compress_document(file: UploadFile) -> tuple[bytes, str, str]:
    from app.helpers.file_upload import ALLOWED_DOCUMENT_FILE_TYPES
    from app.helpers.document_compression import compress_image_to_limit, compress_pdf_to_limit

    if not file.content_type or file.content_type not in ALLOWED_DOCUMENT_FILE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported document type")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

    final_content = content
    final_mime = file.content_type
    final_name = file.filename or "document"

    if len(content) > MAX_STUDENT_DOCUMENT_SIZE_BYTES:
        content_type = file.content_type or ""
        try:
            if content_type.startswith("image/"):
                final_content, final_mime, final_name = compress_image_to_limit(
                    content,
                    final_name,
                    MAX_STUDENT_DOCUMENT_SIZE_BYTES,
                )
            elif content_type == "application/pdf":
                final_content, final_mime, final_name = compress_pdf_to_limit(
                    content,
                    final_name,
                    MAX_STUDENT_DOCUMENT_SIZE_BYTES,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File exceeds 100KB. Automatic compression is available for image and PDF documents only.",
                )
        except HTTPException:
            raise
        except ValueError as exc:
            message = str(exc)
            if "image" in message.lower():
                detail = "Could not compress image to 100KB. Please upload a smaller file."
            elif "pdf" in message.lower():
                detail = "Could not compress PDF to 100KB. Please upload a smaller file."
            else:
                detail = message
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        except Exception as exc:
            if content_type.startswith("image/"):
                detail = "Could not process image for compression."
            elif content_type == "application/pdf":
                detail = "Could not process PDF for compression."
            else:
                detail = "Could not process document for compression."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    if len(final_content) > MAX_STUDENT_DOCUMENT_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Final file size exceeds 100KB")
    return final_content, final_mime, final_name


def _persist_student_document(
    *,
    db: Session,
    student,
    file_name: str,
    file_mime: str,
    content: bytes,
    file_kind: str,
    file_side: Optional[str] = None,
) -> StudentUploadedDocument:
    from app.helpers.file_upload import generate_filename, sanitize_domain
    from app.apis.uploads import get_tenant_domain

    tenant_domain = get_tenant_domain(student.institution_id)
    upload_subdir = "student_documents"
    sanitized_domain = sanitize_domain(tenant_domain)
    filename = generate_filename(file_name, sanitized_domain, "student_document")
    base_upload_dir = os.path.join(os.getcwd(), "uploads")
    upload_dir = os.path.join(base_upload_dir, upload_subdir)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    relative_path = os.path.join(upload_subdir, filename).replace("\\", "/")

    row = StudentUploadedDocument(
        institution_id=student.institution_id,
        student_id=student.id,
        file_name=file_name,
        file_path=relative_path,
        mime_type=file_mime,
        file_size=len(content),
        document_kind=file_kind,
        document_side=file_side,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

# General file upload endpoint
@upload_router.post("/uploads/files")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    category: str = Form(...),  # e.g., 'assignments', 'complaints', 'documents'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    General file upload endpoint
    
    Uploads a file to the appropriate directory based on category and returns the file URL.
    Files are saved to uploads/{category}/ directory.
    
    Args:
        file: The file to upload
        category: Category of file (assignments, complaints, documents, etc.)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with file_url and file_path
    """
    from app.helpers.file_upload import save_uploaded_file, get_file_url
    from app.apis.uploads import get_tenant_domain
    from fastapi import Request
    
    # Get tenant domain for file prefixing
    institution_id = current_user.institution_id if current_user else None
    tenant_domain = get_tenant_domain(institution_id) if institution_id else "default"
    
    # Save the file
    file_path, relative_path = await save_uploaded_file(
        file=file,
        tenant_domain=tenant_domain,
        file_category=category
    )
    
    # Generate file URL
    file_url = get_file_url(relative_path)
    
    return {
        "file_url": file_url,
        "file_path": relative_path,
        "filename": file.filename,
        "category": category
    }


@upload_router.get("/student/documents")
def list_student_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    from app.helpers.file_upload import get_file_url

    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    rows = (
        db.query(StudentUploadedDocument)
        .filter(
            StudentUploadedDocument.institution_id == student.institution_id,
            StudentUploadedDocument.student_id == student.id,
            StudentUploadedDocument.document_kind == "general",
            StudentUploadedDocument.deleted_at.is_(None),
        )
        .order_by(StudentUploadedDocument.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "file_name": row.file_name,
                "file_path": row.file_path,
                "file_url": get_file_url(row.file_path),
                "mime_type": row.mime_type,
                "file_size": row.file_size,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "max_documents": MAX_STUDENT_DOCUMENTS,
        "max_file_size_bytes": MAX_STUDENT_DOCUMENT_SIZE_BYTES,
    }


@upload_router.post("/student/documents")
async def upload_student_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    from app.helpers.file_upload import get_file_url

    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    current_count = (
        db.query(StudentUploadedDocument)
        .filter(
            StudentUploadedDocument.institution_id == student.institution_id,
            StudentUploadedDocument.student_id == student.id,
            StudentUploadedDocument.document_kind == "general",
            StudentUploadedDocument.deleted_at.is_(None),
        )
        .count()
    )
    if current_count >= MAX_STUDENT_DOCUMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {MAX_STUDENT_DOCUMENTS} documents allowed",
        )

    final_content, final_mime, final_name = _read_and_compress_document(file)
    row = _persist_student_document(
        db=db,
        student=student,
        file_name=final_name,
        file_mime=final_mime,
        content=final_content,
        file_kind="general",
    )

    return {
        "id": row.id,
        "file_name": row.file_name,
        "file_url": get_file_url(row.file_path),
        "file_path": row.file_path,
        "mime_type": row.mime_type,
        "file_size": row.file_size,
        "max_documents": MAX_STUDENT_DOCUMENTS,
        "max_file_size_bytes": MAX_STUDENT_DOCUMENT_SIZE_BYTES,
    }


@upload_router.delete("/student/documents/{document_id}")
def delete_student_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    from app.helpers.file_upload import delete_file

    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    row = (
        db.query(StudentUploadedDocument)
        .filter(
            StudentUploadedDocument.id == document_id,
            StudentUploadedDocument.institution_id == student.institution_id,
            StudentUploadedDocument.student_id == student.id,
            StudentUploadedDocument.document_kind == "general",
            StudentUploadedDocument.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        delete_file(row.file_path)
    except Exception:
        pass
    row.deleted_at = datetime.utcnow()
    db.add(row)
    db.commit()
    return {"deleted": True, "document_id": document_id}


@upload_router.get("/student/id-card")
def get_student_id_card_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    from app.helpers.file_upload import get_file_url

    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    rows = (
        db.query(StudentUploadedDocument)
        .filter(
            StudentUploadedDocument.institution_id == student.institution_id,
            StudentUploadedDocument.student_id == student.id,
            StudentUploadedDocument.document_kind == "id_card",
            StudentUploadedDocument.deleted_at.is_(None),
        )
        .all()
    )
    side_map = {"front": None, "back": None}
    for row in rows:
        if row.document_side in side_map:
            side_map[row.document_side] = {
                "id": row.id,
                "file_name": row.file_name,
                "file_url": get_file_url(row.file_path),
                "file_size": row.file_size,
                "mime_type": row.mime_type,
            }
    return {"front": side_map["front"], "back": side_map["back"], "max_file_size_bytes": MAX_STUDENT_DOCUMENT_SIZE_BYTES}


@upload_router.post("/student/id-card")
async def upload_student_id_card_side(
    side: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    from app.helpers.file_upload import get_file_url, delete_file

    side = str(side or "").strip().lower()
    if side not in ID_CARD_SIDES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="side must be 'front' or 'back'")
    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    existing = (
        db.query(StudentUploadedDocument)
        .filter(
            StudentUploadedDocument.institution_id == student.institution_id,
            StudentUploadedDocument.student_id == student.id,
            StudentUploadedDocument.document_kind == "id_card",
            StudentUploadedDocument.document_side == side,
            StudentUploadedDocument.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        try:
            delete_file(existing.file_path)
        except Exception:
            pass
        existing.deleted_at = datetime.utcnow()
        db.add(existing)
        db.commit()

    final_content, final_mime, final_name = _read_and_compress_document(file)
    row = _persist_student_document(
        db=db,
        student=student,
        file_name=final_name,
        file_mime=final_mime,
        content=final_content,
        file_kind="id_card",
        file_side=side,
    )
    return {
        "side": side,
        "id": row.id,
        "file_name": row.file_name,
        "file_url": get_file_url(row.file_path),
        "file_size": row.file_size,
    }


@upload_router.get("/student/id-card/download")
def download_student_id_card_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from fastapi.responses import StreamingResponse

    student = resolve_student_for_logged_in_user(db, current_user)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    rows = (
        db.query(StudentUploadedDocument)
        .filter(
            StudentUploadedDocument.institution_id == student.institution_id,
            StudentUploadedDocument.student_id == student.id,
            StudentUploadedDocument.document_kind == "id_card",
            StudentUploadedDocument.deleted_at.is_(None),
        )
        .all()
    )
    side_paths = {row.document_side: row.file_path for row in rows if row.document_side in ID_CARD_SIDES}
    if not side_paths.get("front") or not side_paths.get("back"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload both front and back ID card images first")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    for side in ("front", "back"):
        abs_path = os.path.join(os.getcwd(), "uploads", side_paths[side])
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{side} image file not found")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, height - 40, f"Student ID Card - {side.capitalize()}")
        image = ImageReader(abs_path)
        img_w, img_h = image.getSize()
        max_w = width - 80
        max_h = height - 120
        ratio = min(max_w / img_w, max_h / img_h)
        draw_w = img_w * ratio
        draw_h = img_h * ratio
        x = (width - draw_w) / 2
        y = (height - draw_h) / 2 - 20
        c.drawImage(image, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
        c.showPage()
    c.save()
    buffer.seek(0)
    filename = f"id_card_{student.student_id or student.id}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@upload_router.post("/uploads/tenant-logo", response_model=TenantSettingsResponse)
async def upload_logo_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Upload tenant logo (admin/super_admin only)
    
    The uploaded file will be prefixed with the tenant domain for easy sorting and fetching.
    The logo URL will be stored in both tenant_settings and tenant tables.
    """
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to upload tenant logo"
        )
    
    # Get global database session for tenant table update
    from app.database.base import get_db_session
    global_db = next(get_db_session())
    
    try:
        settings = await upload_tenant_logo(
            db=db,
            institution_id=current_user.institution_id,
            file=file,
            tenant_db=global_db  # Pass global database for tenant table update
        )
        
        return TenantSettingsResponse.model_validate(settings)
    finally:
        global_db.close()


@upload_router.delete("/uploads/tenant-logo", response_model=TenantSettingsResponse)
def delete_logo_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Delete tenant logo (admin/super_admin only)
    """
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to delete tenant logo"
        )
    
    settings = delete_tenant_logo(
        db=db,
        institution_id=current_user.institution_id
    )
    
    return TenantSettingsResponse.model_validate(settings)


@upload_router.post("/uploads/profile-picture", response_model=UserResponse)
async def upload_profile_picture_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Upload current user's profile picture
    
    The uploaded file will be prefixed with the tenant domain for easy sorting and fetching.
    Users can upload their own profile picture, or admins can upload for other users.
    """
    user = await upload_profile_picture(
        db=db,
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        file=file
    )
    
    # Convert to response model
    return UserResponse.model_validate(user)


@upload_router.post("/uploads/users/{user_id}/profile-picture", response_model=UserResponse)
async def upload_user_profile_picture_endpoint(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """
    Upload profile picture for a specific user (admin/secretary/super_admin only)
    
    The uploaded file will be prefixed with the tenant domain for easy sorting and fetching.
    """
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    target_user = get_user(db=db, user_id=user_id, institution_id=institution_id)
    
    # Check if admin is trying to upload for a user from a different institution
    if not user_is_system_admin(current_user):
        if target_user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload profile pictures for users in your institution"
            )
    
    user = await upload_profile_picture(
        db=db,
        user_id=user_id,
        institution_id=target_user.institution_id,
        file=file
    )
    
    return UserResponse.model_validate(user)


@upload_router.delete("/uploads/profile-picture", response_model=UserResponse)
def delete_profile_picture_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Delete current user's profile picture
    """
    user = delete_profile_picture(
        db=db,
        user_id=current_user.id
    )
    
    return UserResponse.model_validate(user)


@upload_router.delete("/uploads/users/{user_id}/profile-picture", response_model=UserResponse)
def delete_user_profile_picture_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """
    Delete profile picture for a specific user (admin/secretary/super_admin only)
    """
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    target_user = get_user(db=db, user_id=user_id, institution_id=institution_id)
    
    # Check if admin is trying to delete for a user from a different institution
    if not user_is_system_admin(current_user):
        if target_user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete profile pictures for users in your institution"
            )
    
    user = delete_profile_picture(
        db=db,
        user_id=user_id
    )
    
    return UserResponse.model_validate(user)


@upload_router.get("/uploads/{file_path:path}")
async def serve_uploaded_file(
    file_path: str,
    origin: str = Header(None)
):
    """
    Serve uploaded files dynamically (logos, profile pictures, etc.)
    
    This endpoint is public and does not require authentication.
    Files are served based on their relative path from the uploads directory.
    The file_path parameter is dynamic and accepts any path structure.
    
    Examples:
    - /api/v1/uploads/logos/tenant_domain_logo_20240101_120000_abc123.jpg
    - /api/v1/uploads/profile_pictures/user_profile.jpg
    - /api/v1/uploads/logos/subfolder/file.png
    """
    # Security: Prevent directory traversal
    # Remove leading slash if present (URLs might have it)
    file_path = file_path.lstrip('/')
    if '..' in file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    # Construct full file path
    base_upload_dir = os.path.join(os.getcwd(), 'uploads')
    full_path = os.path.join(base_upload_dir, file_path)
    
    # Normalize path to prevent directory traversal
    full_path = os.path.normpath(full_path)
    base_upload_dir = os.path.normpath(base_upload_dir)
    
    # Ensure the file is within the uploads directory
    if not full_path.startswith(base_upload_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if file exists
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        # Try to find the file in the directory (case-insensitive search)
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        
        if os.path.exists(directory) and os.path.isdir(directory):
            # List files in the directory and try case-insensitive match
            try:
                files = os.listdir(directory)
                # Try exact match first
                if filename in files:
                    full_path = os.path.join(directory, filename)
                else:
                    # Try case-insensitive match
                    for f in files:
                        if f.lower() == filename.lower():
                            full_path = os.path.join(directory, f)
                            break
                    else:
                        # File not found even with case-insensitive search
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File not found: {file_path}"
                        )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_path}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
    
    # Determine content type based on file extension
    file_ext = Path(full_path).suffix.lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    
    content_type = content_types.get(file_ext, 'application/octet-stream')
    
    # Read file and return with CORS headers
    with open(full_path, 'rb') as f:
        file_content = f.read()
    
    return Response(
        content=file_content,
        media_type=content_type,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Content-Disposition': f'inline; filename="{os.path.basename(full_path)}"'
        }
    )
