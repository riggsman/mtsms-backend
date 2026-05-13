"""Payroll clock sessions and reporting (hours × hourly rate)."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
import random
from typing import List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, aliased

from app.conf.config import settings
from app.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.exceptions.exceptions import BadRequestError
from app.helpers.pagination import paginate_query
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.payroll_time_entry import PayrollTimeEntry
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User

MAX_SESSION_HOURS = Decimal("24")
CODE_TTL_MINUTES = 30


def _parse_date_param(value: str, label: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.strip())
        if len(value.strip()) == 10:
            return d
        return d
    except ValueError as e:
        raise ValidationError(f"Invalid {label} date (use YYYY-MM-DD): {value}") from e


def _day_start_utc(d: datetime) -> datetime:
    if d.tzinfo is not None:
        d = d.replace(tzinfo=None)
    return datetime(d.year, d.month, d.day)


def _day_end_utc(d: datetime) -> datetime:
    start = _day_start_utc(d)
    return start + timedelta(days=1) - timedelta(microseconds=1)


def resolve_teacher_for_user(db: Session, user: User) -> Optional[Teacher]:
    if not user or user.institution_id is None:
        return None
    return (
        db.query(Teacher)
        .filter(
            Teacher.email == user.email,
            Teacher.institution_id == user.institution_id,
            Teacher.deleted_at.is_(None),
        )
        .first()
    )


def compute_duration_hours(clock_in_at: datetime, clock_out_at: datetime) -> Decimal:
    delta = clock_out_at - clock_in_at
    hours = Decimal(str(delta.total_seconds())) / Decimal("3600")
    if hours < 0:
        hours = Decimal("0")
    if hours > MAX_SESSION_HOURS:
        hours = MAX_SESSION_HOURS
    return hours.quantize(Decimal("0.01"))


def _hash_code(raw_code: str) -> str:
    payload = f"{settings.SECRET_KEY}:{raw_code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _code_matches(raw_code: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    return hmac.compare_digest(_hash_code(raw_code), hashed)


def _generate_5_digit_code() -> str:
    return f"{random.randint(0, 99999):05d}"


def _assert_code_not_expired(entry: PayrollTimeEntry) -> None:
    if entry.codes_expires_at and datetime.utcnow() > entry.codes_expires_at:
        raise ConflictError("Clock code has expired. Request a new one from admin.")


def _resolve_course_by_code(db: Session, institution_id: int, course_code: str) -> Course:
    course = (
        db.query(Course)
        .filter(
            Course.code == course_code.strip(),
            Course.institution_id == institution_id,
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise NotFoundError("Course not found for this institution.")
    return course


def resolve_student_for_user(db: Session, user: User) -> Optional[Student]:
    """Match GET /students/me resolution (email case, username/matricule fallbacks)."""
    if not user or user.institution_id is None:
        return None
    from app.apis.students import resolve_student_for_logged_in_user

    return resolve_student_for_logged_in_user(db, user)


def generate_codes(
    db: Session,
    current_user: User,
    teacher_id: int,
    course_code: str,
    expires_in_minutes: int = CODE_TTL_MINUTES,
) -> dict:
    teacher_query = db.query(Teacher).filter(Teacher.id == teacher_id, Teacher.deleted_at.is_(None))
    if current_user.institution_id:
        teacher_query = teacher_query.filter(Teacher.institution_id == current_user.institution_id)
    teacher = teacher_query.first()
    if not teacher:
        raise NotFoundError("Lecturer not found in this institution.")
    course = _resolve_course_by_code(db, teacher.institution_id, course_code)
    existing_open = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.teacher_id == teacher.id,
            PayrollTimeEntry.institution_id == teacher.institution_id,
            PayrollTimeEntry.clock_out_at.is_(None),
            PayrollTimeEntry.deleted_at.is_(None),
        )
        .first()
    )
    if existing_open:
        raise ConflictError("Lecturer already has an active session.")

    in_code = _generate_5_digit_code()
    out_code = _generate_5_digit_code()
    now = datetime.utcnow()
    ttl = int(expires_in_minutes) if expires_in_minutes else CODE_TTL_MINUTES
    ttl = max(1, min(ttl, 24 * 60))
    expires_at = now + timedelta(minutes=ttl)
    entry = PayrollTimeEntry(
        institution_id=teacher.institution_id,
        teacher_id=teacher.id,
        course_id=course.id,
        course_code_snapshot=course.code,
        clock_in_code_hash=_hash_code(in_code),
        clock_out_code_hash=_hash_code(out_code),
        clock_in_code_plain=in_code,
        clock_out_code_plain=out_code,
        codes_generated_by_user_id=current_user.id,
        codes_generated_at=now,
        codes_expires_at=expires_at,
        clock_in_at=now,
        clock_out_at=None,
        duration_hours=None,
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "entry_id": entry.id,
        "teacher_id": teacher.id,
        "course_id": course.id,
        "course_code": course.code,
        "clock_in_code": in_code,
        "clock_out_code": out_code,
        "expires_at": expires_at,
    }


def auto_generate_codes_for_schedule(
    db: Session,
    institution_id: int,
    teacher_id: int,
    course_code: str,
    generated_by_user_id: int = 0,
    regenerate_clockout_only: bool = False,
) -> Optional[PayrollTimeEntry]:
    teacher = (
        db.query(Teacher)
        .filter(
            Teacher.id == teacher_id,
            Teacher.institution_id == institution_id,
            Teacher.deleted_at.is_(None),
        )
        .first()
    )
    if not teacher:
        return None
    course = _resolve_course_by_code(db, institution_id, course_code)
    open_entry = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.teacher_id == teacher.id,
            PayrollTimeEntry.institution_id == institution_id,
            PayrollTimeEntry.clock_out_at.is_(None),
            PayrollTimeEntry.deleted_at.is_(None),
            PayrollTimeEntry.course_code_snapshot == course.code,
        )
        .order_by(PayrollTimeEntry.created_at.desc())
        .first()
    )
    now = datetime.utcnow()
    if regenerate_clockout_only:
        if not open_entry:
            return None
        out_code = _generate_5_digit_code()
        open_entry.clock_out_code_hash = _hash_code(out_code)
        open_entry.clock_out_code_plain = out_code
        open_entry.codes_generated_at = now
        open_entry.codes_expires_at = now + timedelta(minutes=CODE_TTL_MINUTES)
        open_entry.updated_at = now
        db.commit()
        db.refresh(open_entry)
        return open_entry

    if open_entry:
        return open_entry

    in_code = _generate_5_digit_code()
    out_code = _generate_5_digit_code()
    entry = PayrollTimeEntry(
        institution_id=institution_id,
        teacher_id=teacher.id,
        course_id=course.id,
        course_code_snapshot=course.code,
        clock_in_code_hash=_hash_code(in_code),
        clock_out_code_hash=_hash_code(out_code),
        clock_in_code_plain=in_code,
        clock_out_code_plain=out_code,
        codes_generated_by_user_id=generated_by_user_id,
        codes_generated_at=now,
        codes_expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
        clock_in_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def clock_in_with_code(db: Session, user: User, course_code: str, clock_in_code: str) -> PayrollTimeEntry:
    teacher = resolve_teacher_for_user(db, user)
    if not teacher:
        raise ForbiddenError("No lecturer profile is linked to this account (matching email and institution).")

    open_entry = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.teacher_id == teacher.id,
            PayrollTimeEntry.institution_id == teacher.institution_id,
            PayrollTimeEntry.clock_out_at.is_(None),
            PayrollTimeEntry.deleted_at.is_(None),
        )
        .order_by(PayrollTimeEntry.created_at.desc())
        .first()
    )
    if not open_entry:
        raise BadRequestError("No generated code session was found for this lecturer.")
    if (open_entry.course_code_snapshot or "").strip() != course_code.strip():
        raise ValidationError("Provided course code does not match active generated session.")
    _assert_code_not_expired(open_entry)
    if not _code_matches(clock_in_code, open_entry.clock_in_code_hash):
        raise ForbiddenError("Invalid clock-in code.")

    now = datetime.utcnow()
    open_entry.clock_in_at = now
    open_entry.clock_in_code_hash = None
    open_entry.clock_in_code_plain = None
    open_entry.clock_in_code_used_at = now
    open_entry.updated_at = now
    db.commit()
    db.refresh(open_entry)
    return open_entry


def lecturer_clock_out_confirm(
    db: Session, user: User, course_code: str, clock_out_code: str
) -> PayrollTimeEntry:
    teacher = resolve_teacher_for_user(db, user)
    if not teacher:
        raise ForbiddenError("No lecturer profile is linked to this account (matching email and institution).")

    open_entry = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.teacher_id == teacher.id,
            PayrollTimeEntry.institution_id == teacher.institution_id,
            PayrollTimeEntry.clock_out_at.is_(None),
            PayrollTimeEntry.deleted_at.is_(None),
        )
        .order_by(PayrollTimeEntry.clock_in_at.desc())
        .first()
    )
    if not open_entry:
        raise ConflictError("No open clock-in session to close.")
    if open_entry.lecturer_clock_out_confirmed_at:
        raise ConflictError("Lecturer clock-out confirmation already submitted.")
    if (open_entry.course_code_snapshot or "").strip() != course_code.strip():
        raise ValidationError("Provided course code does not match active session.")
    _assert_code_not_expired(open_entry)
    if not open_entry.student_clock_out_confirmed_at:
        if not _code_matches(clock_out_code, open_entry.clock_out_code_hash):
            raise ForbiddenError("Invalid clock-out code.")

    now = datetime.utcnow()
    open_entry.lecturer_clock_out_confirmed_at = now
    open_entry.clock_out_code_hash = None
    open_entry.clock_out_code_plain = None
    if open_entry.clock_out_code_used_at is None:
        open_entry.clock_out_code_used_at = now
    if open_entry.student_clock_out_confirmed_at:
        open_entry.clock_out_finalized_at = now
        open_entry.clock_out_at = now
        open_entry.duration_hours = compute_duration_hours(open_entry.clock_in_at, now)
    open_entry.updated_at = now
    db.commit()
    db.refresh(open_entry)
    return open_entry


def student_clock_out_confirm(
    db: Session, user: User, course_code: str, clock_out_code: str
) -> PayrollTimeEntry:
    student = resolve_student_for_user(db, user)
    if not student:
        raise ForbiddenError("No student profile is linked to this account.")

    open_entry = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.institution_id == student.institution_id,
            PayrollTimeEntry.clock_out_at.is_(None),
            PayrollTimeEntry.deleted_at.is_(None),
            PayrollTimeEntry.course_code_snapshot == course_code.strip(),
        )
        .order_by(PayrollTimeEntry.clock_in_at.desc())
        .first()
    )
    if not open_entry:
        # Treat invalid/mismatched student clock-out token inputs as forbidden instead of 404.
        # Returning 404 here leaks little value and breaks clients expecting auth/validation errors.
        raise ForbiddenError("Invalid clock-out code or course code.")
    if open_entry.student_clock_out_confirmed_at:
        raise ConflictError("Clock-out student confirmation already submitted.")
    _assert_code_not_expired(open_entry)
    if not open_entry.lecturer_clock_out_confirmed_at:
        if not _code_matches(clock_out_code, open_entry.clock_out_code_hash):
            raise ForbiddenError("Invalid clock-out code.")

    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.institution_id == student.institution_id,
            Enrollment.student_id == student.id,
            Enrollment.course_id == open_entry.course_id,
            Enrollment.deleted_at.is_(None),
            Enrollment.status == "active",
        )
        .first()
    )
    if not enrollment:
        raise ForbiddenError("Student is not actively enrolled in this course.")

    now = datetime.utcnow()
    if open_entry.student_confirmer_id and open_entry.student_confirmer_id != student.id:
        raise ConflictError("Clock-out student confirmation already submitted.")
    open_entry.student_confirmer_id = student.id
    open_entry.student_clock_out_confirmed_at = now
    open_entry.clock_out_code_hash = None
    open_entry.clock_out_code_plain = None
    if open_entry.clock_out_code_used_at is None:
        open_entry.clock_out_code_used_at = now
    if open_entry.lecturer_clock_out_confirmed_at:
        open_entry.clock_out_finalized_at = now
        open_entry.clock_out_at = now
        open_entry.duration_hours = compute_duration_hours(open_entry.clock_in_at, now)
    open_entry.updated_at = now
    db.commit()
    db.refresh(open_entry)
    return open_entry


def get_clock_status(
    db: Session, user: User,
) -> Tuple[bool, Optional[int], Optional[datetime], Optional[str], bool, Optional[str], Optional[str]]:
    teacher = resolve_teacher_for_user(db, user)
    if not teacher:
        return False, None, None, None, False, None, None
    open_entry = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.teacher_id == teacher.id,
            PayrollTimeEntry.institution_id == teacher.institution_id,
            PayrollTimeEntry.clock_out_at.is_(None),
            PayrollTimeEntry.deleted_at.is_(None),
        )
        .order_by(PayrollTimeEntry.clock_in_at.desc())
        .first()
    )
    if not open_entry:
        return False, None, None, None, False, None, None
    waiting_student = bool(
        open_entry.lecturer_clock_out_confirmed_at
        and not open_entry.student_clock_out_confirmed_at
        and not open_entry.clock_out_at
    )
    cin_plain = open_entry.clock_in_code_plain or None
    cout_plain = open_entry.clock_out_code_plain or None
    return (
        True,
        open_entry.id,
        open_entry.clock_in_at,
        open_entry.course_code_snapshot,
        waiting_student,
        cin_plain,
        cout_plain,
    )


def list_my_entries(
    db: Session,
    user: User,
    from_date: Optional[str],
    to_date: Optional[str],
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[PayrollTimeEntry], int]:
    teacher = resolve_teacher_for_user(db, user)
    if not teacher:
        raise ForbiddenError("No lecturer profile is linked to this account.")

    q = (
        db.query(PayrollTimeEntry)
        .filter(
            PayrollTimeEntry.teacher_id == teacher.id,
            PayrollTimeEntry.institution_id == teacher.institution_id,
            PayrollTimeEntry.deleted_at.is_(None),
        )
    )
    if from_date:
        start = _day_start_utc(_parse_date_param(from_date, "from"))
        q = q.filter(PayrollTimeEntry.clock_in_at >= start)
    if to_date:
        end = _day_end_utc(_parse_date_param(to_date, "to"))
        q = q.filter(PayrollTimeEntry.clock_in_at <= end)

    q = q.order_by(PayrollTimeEntry.clock_in_at.desc())
    return paginate_query(q, page=page, page_size=page_size)


def payroll_report(
    db: Session,
    current_user: User,
    from_date: str,
    to_date: str,
    teacher_id: Optional[int] = None,
) -> List[dict]:
    if not current_user.institution_id:
        raise ValidationError("Institution context is required for payroll report.")

    start = _day_start_utc(_parse_date_param(from_date, "from"))
    end = _day_end_utc(_parse_date_param(to_date, "to"))

    base_filters = [
        Teacher.institution_id == current_user.institution_id,
        Teacher.deleted_at.is_(None),
        PayrollTimeEntry.institution_id == current_user.institution_id,
        PayrollTimeEntry.deleted_at.is_(None),
        PayrollTimeEntry.clock_out_at.isnot(None),
        PayrollTimeEntry.clock_out_finalized_at.isnot(None),
        PayrollTimeEntry.duration_hours.isnot(None),
        PayrollTimeEntry.clock_out_at >= start,
        PayrollTimeEntry.clock_out_at <= end,
    ]
    if teacher_id is not None:
        base_filters.append(Teacher.id == teacher_id)

    rows = (
        db.query(
            Teacher.id.label("teacher_id"),
            Teacher.firstname,
            Teacher.lastname,
            Teacher.employee_id,
            Teacher.hourly_rate,
            func.coalesce(func.sum(PayrollTimeEntry.duration_hours), 0).label("total_hours"),
        )
        .join(PayrollTimeEntry, PayrollTimeEntry.teacher_id == Teacher.id)
        .filter(and_(*base_filters))
        .group_by(
            Teacher.id,
            Teacher.firstname,
            Teacher.lastname,
            Teacher.employee_id,
            Teacher.hourly_rate,
        )
        .all()
    )

    out: List[dict] = []
    for r in rows:
        total_h = Decimal(str(r.total_hours)) if r.total_hours is not None else Decimal("0")
        rate = r.hourly_rate
        gross: Optional[Decimal] = None
        if rate is not None:
            gross = (total_h * Decimal(str(rate))).quantize(Decimal("0.01"))
        out.append(
            {
                "teacher_id": r.teacher_id,
                "firstname": r.firstname,
                "lastname": r.lastname,
                "employee_id": r.employee_id,
                "hourly_rate": Decimal(str(rate)) if rate is not None else None,
                "total_hours": total_h.quantize(Decimal("0.01")),
                "gross_pay": gross,
            }
        )
    return out


def list_payroll_codes_audit(
    db: Session,
    current_user: User,
    from_date: str,
    to_date: str,
    teacher_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[dict], int]:
    """Rows where clock codes were issued (codes_generated_at), for admin traceability."""
    if not current_user.institution_id:
        raise ValidationError("Institution context is required for payroll code audit.")

    start = _day_start_utc(_parse_date_param(from_date, "from"))
    end = _day_end_utc(_parse_date_param(to_date, "to"))

    GenUser = aliased(User)
    q = (
        db.query(PayrollTimeEntry, Teacher, GenUser)
        .join(Teacher, Teacher.id == PayrollTimeEntry.teacher_id)
        .outerjoin(GenUser, GenUser.id == PayrollTimeEntry.codes_generated_by_user_id)
        .filter(
            PayrollTimeEntry.institution_id == current_user.institution_id,
            PayrollTimeEntry.deleted_at.is_(None),
            PayrollTimeEntry.codes_generated_at.isnot(None),
            PayrollTimeEntry.codes_generated_at >= start,
            PayrollTimeEntry.codes_generated_at <= end,
        )
    )
    if teacher_id is not None:
        q = q.filter(PayrollTimeEntry.teacher_id == teacher_id)

    q = q.order_by(PayrollTimeEntry.codes_generated_at.desc())
    rows, total = paginate_query(q, page=page, page_size=page_size)

    out: List[dict] = []
    for entry, teacher, gen_user in rows:
        gen_name = None
        if gen_user:
            gen_name = f"{(gen_user.firstname or '').strip()} {(gen_user.lastname or '').strip()}".strip()
            if not gen_name:
                gen_name = (gen_user.username or "").strip() or None

        clock_in_used = entry.clock_in_code_hash is None
        clock_out_used = entry.clock_out_code_hash is None

        out.append(
            {
                "entry_id": entry.id,
                "teacher_id": teacher.id,
                "teacher_name": f"{(teacher.firstname or '').strip()} {(teacher.lastname or '').strip()}".strip(),
                "course_code": entry.course_code_snapshot,
                "codes_generated_at": entry.codes_generated_at,
                "codes_expires_at": entry.codes_expires_at,
                "generated_by_user_id": entry.codes_generated_by_user_id,
                "generated_by_name": gen_name,
                "clock_in_code_plain": entry.clock_in_code_plain,
                "clock_out_code_plain": entry.clock_out_code_plain,
                "clock_in_code_used": clock_in_used,
                "clock_out_code_used": clock_out_used,
                "clock_in_code_used_at": entry.clock_in_code_used_at,
                "clock_out_code_used_at": entry.clock_out_code_used_at,
            }
        )
    return out, total
