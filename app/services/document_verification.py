"""Issue and verify academic PDFs (transcript, result slip) via QR codes."""
from __future__ import annotations

import io
import json
import os
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.verified_document import VerifiedDocument
from app.schemas.document_verification import (
    DocumentPublicVerificationResponse,
    VerifiedDocumentCourseItem,
    VerifiedDocumentStudent,
    VerifiedDocumentSummary,
)


def _public_app_base_url() -> str:
    base = (
        os.getenv("PUBLIC_APP_URL")
        or os.getenv("FRONTEND_URL")
        or os.getenv("APP_PUBLIC_URL")
        or "http://localhost:5173"
    )
    return str(base).rstrip("/")


def build_document_verification_url(verification_token: str) -> str:
    token = (verification_token or "").strip()
    if not token:
        return ""
    return f"{_public_app_base_url()}/verify-document?v={token}"


def _new_verification_token() -> str:
    return secrets.token_urlsafe(32)


def _serialize_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, default=str)


def _deserialize_payload(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def register_verified_document(
    db: Session,
    *,
    document_type: str,
    institution_id: int,
    student_no: str,
    payload: Dict[str, Any],
    student_id: Optional[int] = None,
    semester: Optional[str] = None,
    verification_token: Optional[str] = None,
) -> str:
    """Persist verification record and return token for QR URL."""
    token = (verification_token or "").strip() or _new_verification_token()
    issued_at = datetime.utcnow()
    payload = {**payload, "issued_at": issued_at.isoformat()}
    row = VerifiedDocument(
        verification_token=token,
        document_type=document_type,
        institution_id=institution_id,
        student_id=student_id,
        student_no=student_no,
        semester=semester,
        payload_json=_serialize_payload(payload),
        issued_at=issued_at,
        created_at=issued_at,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except Exception as exc:
        db.rollback()
        raise RuntimeError(
            "Failed to save document verification record. "
            "Run database migrations (alembic upgrade head), including verified_documents."
        ) from exc
    return token


def _require_qr_dependencies():
    """Import QR/PIL libraries or raise a clear install hint."""
    try:
        import qrcode  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "QR code support requires qrcode and Pillow. Install with: pip install 'qrcode[pil]'"
        ) from exc


def build_verification_qr_png_bytes(verification_url: str) -> bytes:
    """Build a PNG byte stream for a verification URL (validates QR can be rendered)."""
    _require_qr_dependencies()
    import qrcode
    from PIL import Image

    url = (verification_url or "").strip()
    if not url:
        raise ValueError("Verification URL is empty")

    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    pil_img = img.get_image() if hasattr(img, "get_image") else img
    if getattr(pil_img, "mode", None) not in ("RGB", "L"):
        pil_img = pil_img.convert("RGB")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def draw_verification_qr_png_on_canvas(
    canvas_obj,
    png_bytes: bytes,
    *,
    x: float,
    y: float,
    size: float = 0.95 * inch,
    label: str = "Scan to verify",
) -> None:
    """Draw a pre-built verification QR PNG onto a ReportLab canvas."""
    if not png_bytes:
        raise ValueError("QR image bytes are empty")
    buf = io.BytesIO(png_bytes)
    canvas_obj.drawImage(ImageReader(buf), x, y, width=size, height=size)
    if label:
        try:
            canvas_obj.setFont("Helvetica", 7)
            canvas_obj.drawString(x, max(y - 0.12 * inch, 0.15 * inch), label)
        except Exception as label_exc:
            print(f"[document_verification] QR label skipped: {label_exc}")


def issue_verified_document(
    db: Session,
    *,
    document_type: str,
    institution_id: int,
    student_no: str,
    payload: Dict[str, Any],
    student_id: Optional[int] = None,
    semester: Optional[str] = None,
) -> Tuple[str, bytes]:
    """
    Pre-build QR PNG, persist verification record, return (token, png_bytes).
    Fails before DB write if QR libraries or rendering are unavailable.
    """
    token = _new_verification_token()
    url = build_document_verification_url(token)
    png_bytes = build_verification_qr_png_bytes(url)
    register_verified_document(
        db,
        document_type=document_type,
        institution_id=institution_id,
        student_no=student_no,
        payload=payload,
        student_id=student_id,
        semester=semester,
        verification_token=token,
    )
    return token, png_bytes


def draw_verification_qr_on_canvas(
    canvas_obj,
    verification_token: str,
    *,
    x: float,
    y: float,
    size: float = 0.95 * inch,
    label: str = "Scan to verify",
    strict: bool = False,
    png_bytes: Optional[bytes] = None,
) -> bool:
    """Draw QR code linking to public verification page (bottom-right of PDF)."""
    if not (verification_token or "").strip() and not png_bytes:
        if strict:
            raise ValueError("Verification token is empty")
        return False
    try:
        if png_bytes is None:
            url = build_document_verification_url(verification_token)
            if not url:
                if strict:
                    raise ValueError("Verification URL is empty")
                return False
            png_bytes = build_verification_qr_png_bytes(url)
        draw_verification_qr_png_on_canvas(
            canvas_obj,
            png_bytes,
            x=x,
            y=y,
            size=size,
            label=label,
        )
        return True
    except ImportError as exc:
        print(f"[document_verification] QR dependencies missing: {exc}")
        if strict:
            raise RuntimeError(str(exc)) from exc
        return False
    except Exception as exc:
        print(f"[document_verification] QR render failed: {exc}")
        if strict:
            raise RuntimeError(f"Unable to render verification QR: {exc}") from exc
        return False


def _institution_name(db: Session, institution_id: int) -> Optional[str]:
    tenant = db.query(Tenant).filter(Tenant.id == institution_id).first()
    return tenant.name if tenant else None


def _payload_to_response(
    row: VerifiedDocument,
    institution_name: Optional[str],
) -> DocumentPublicVerificationResponse:
    payload = _deserialize_payload(row.payload_json)
    student_raw = payload.get("student") or {}
    courses_raw = payload.get("courses") or []
    summary_raw = payload.get("summary") or {}

    courses = [
        VerifiedDocumentCourseItem(**{k: v for k, v in c.items() if k in VerifiedDocumentCourseItem.model_fields})
        for c in courses_raw
        if isinstance(c, dict)
    ]
    summary = (
        VerifiedDocumentSummary(**{k: v for k, v in summary_raw.items() if k in VerifiedDocumentSummary.model_fields})
        if summary_raw
        else None
    )
    student = VerifiedDocumentStudent(
        student_no=student_raw.get("student_no") or row.student_no,
        surname=student_raw.get("surname"),
        other_names=student_raw.get("other_names"),
        full_name=student_raw.get("full_name")
        or " ".join(filter(None, [student_raw.get("surname"), student_raw.get("other_names")])).strip(),
        department=student_raw.get("department"),
        faculty=student_raw.get("faculty"),
        degree_proposed=student_raw.get("degree_proposed"),
        date_of_birth=student_raw.get("date_of_birth"),
        sex=student_raw.get("sex"),
        date_of_enrolment=student_raw.get("date_of_enrolment"),
    )

    issued_at = row.issued_at or datetime.utcnow()
    doc_type = row.document_type or payload.get("document_type") or "document"
    title = payload.get("title") or (
        "ACADEMIC RECORD" if doc_type == "transcript" else "STATEMENT OF RESULTS"
    )

    return DocumentPublicVerificationResponse(
        verified=True,
        document_type=doc_type,
        document_title=title,
        institution_name=institution_name,
        issued_at=issued_at,
        date_printed=payload.get("date_printed"),
        semester=row.semester or payload.get("semester"),
        student=student,
        courses=courses,
        summary=summary,
        verification_message="This document is authentic and was issued by the institution.",
    )


def get_public_document_verification(
    db: Session,
    verification_token: str,
) -> DocumentPublicVerificationResponse:
    token = (verification_token or "").strip()
    if not token:
        raise ValueError("Verification token is required")

    row = (
        db.query(VerifiedDocument)
        .filter(
            VerifiedDocument.verification_token == token,
            VerifiedDocument.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise LookupError("Document not found")

    inst_name = _institution_name(db, row.institution_id)
    return _payload_to_response(row, inst_name)


def build_transcript_verification_payload(
    student_data: Dict[str, Any],
    institution: Dict[str, Any],
    courses: List[Dict[str, Any]],
    *,
    date_printed: str,
    totals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    course_items = [
        {
            "code": c.get("cse_code"),
            "title": c.get("course_title"),
            "semester": c.get("semester"),
            "type": c.get("type"),
            "credit_value": c.get("credit_value"),
            "grade": c.get("grade"),
            "credits_earned": c.get("credits_earned"),
            "points": c.get("points"),
        }
        for c in courses
    ]
    summary = None
    if totals:
        summary = VerifiedDocumentSummary(
            cumulative_gpa=totals.get("cumulative_gpa"),
            total_credits=totals.get("total_credits_attempted"),
            total_credits_earned=totals.get("total_credits_earned"),
        ).model_dump(exclude_none=True)

    return {
        "document_type": "transcript",
        "title": "ACADEMIC RECORD",
        "date_printed": date_printed,
        "student": {
            **student_data,
            "full_name": f"{student_data.get('surname', '')} {student_data.get('other_names', '')}".strip(),
        },
        "institution": institution,
        "courses": course_items,
        "summary": summary,
    }


def build_result_slip_verification_payload(
    student_data: Dict[str, Any],
    institution: Dict[str, Any],
    courses: List[Dict[str, Any]],
    *,
    semester: str,
    date_printed: str,
    semester_gpa: float,
    total_credits: float,
    total_ca: float,
    total_exam: float,
    grand_total: float,
) -> Dict[str, Any]:
    course_items = []
    for c in courses:
        remark = "PASS" if c.get("grade") not in ["F", "X", "W", "N", "P"] else "FAIL"
        course_items.append(
            {
                "code": c.get("cse_code"),
                "title": c.get("course_title"),
                "semester": c.get("semester"),
                "ca_mark": c.get("ca_mark"),
                "exam_mark": c.get("exam_mark"),
                "total_mark": c.get("total_mark"),
                "grade": c.get("grade"),
                "points": c.get("points"),
                "remark": remark,
            }
        )

    return {
        "document_type": "result_slip",
        "title": "STATEMENT OF RESULTS",
        "semester": semester,
        "date_printed": date_printed,
        "student": {
            **student_data,
            "full_name": f"{student_data.get('surname', '')}, {student_data.get('other_names', '')}".strip(", "),
        },
        "institution": institution,
        "courses": course_items,
        "summary": VerifiedDocumentSummary(
            semester_gpa=semester_gpa,
            total_credits=total_credits,
            total_ca=total_ca,
            total_exam=total_exam,
            grand_total=grand_total,
        ).model_dump(exclude_none=True),
    }
