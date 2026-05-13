from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.student_record import StudentRecord
from app.schemas.courses import CoursePerformanceResponse, CourseSchedulePerformanceItem


PASSING_GRADES = {"A", "B", "C", "D"}


def _round_decimal(value: Decimal | float | int, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _parse_time(value: Optional[str]):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _duration_hours(start_time: Optional[str], end_time: Optional[str]) -> Decimal:
    start = _parse_time(start_time)
    end = _parse_time(end_time)
    if not start or not end:
        return Decimal("0")
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    minutes = (end_dt - start_dt).total_seconds() / 60
    if minutes <= 0:
        return Decimal("0")
    return _round_decimal(Decimal(str(minutes)) / Decimal("60"))


def _weekday_index(day_name: Optional[str]) -> Optional[int]:
    days = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    if not day_name:
        return None
    return days.get(str(day_name).strip().lower())


def _occurrences_between(day_name: Optional[str], start: date, end: date) -> int:
    if end < start:
        return 0
    target = _weekday_index(day_name)
    if target is None:
        return 0
    offset = (target - start.weekday()) % 7
    first = start + timedelta(days=offset)
    if first > end:
        return 0
    return ((end - first).days // 7) + 1


def _course_matches_schedule(course: Course, schedule: Schedule) -> bool:
    raw = (schedule.course_name or "").strip().lower()
    if not raw:
        return False
    return raw in {
        (course.name or "").strip().lower(),
        (course.code or "").strip().lower(),
    }


def _course_schedules(db: Session, course: Course) -> list[Schedule]:
    return db.query(Schedule).filter(
        Schedule.institution_id == course.institution_id,
        Schedule.deleted_at.is_(None),
        or_(
            func.lower(Schedule.course_name) == func.lower(course.name),
            func.lower(Schedule.course_name) == func.lower(course.code),
        ),
    ).all()


def _teaching_hours(schedules: Iterable[Schedule], start: Optional[date], end: Optional[date]) -> Decimal:
    if not start or not end or end < start:
        return Decimal("0.00")
    total = Decimal("0.00")
    for schedule in schedules:
        hours = _duration_hours(schedule.start_time, schedule.end_time)
        if hours <= 0:
            continue
        total += hours * _occurrences_between(schedule.day, start, end)
    return _round_decimal(total)


def _percentage(numerator: int | Decimal, denominator: int | Decimal) -> Decimal:
    denominator = Decimal(str(denominator or 0))
    if denominator <= 0:
        return Decimal("0.00")
    value = (Decimal(str(numerator or 0)) / denominator) * Decimal("100")
    if value < 0:
        value = Decimal("0")
    if value > 100:
        value = Decimal("100")
    return _round_decimal(value)


def build_course_performance(db: Session, course: Course, today: Optional[date] = None) -> CoursePerformanceResponse:
    today = today or date.today()
    schedules = [s for s in _course_schedules(db, course) if _course_matches_schedule(course, s)]
    expected_hours = _teaching_hours(schedules, course.start_date, course.expected_end_date)
    elapsed_end = min(today, course.expected_end_date) if course.expected_end_date else today
    elapsed_hours = _teaching_hours(schedules, course.start_date, elapsed_end)
    progress = _percentage(elapsed_hours, expected_hours)

    enrollments = db.query(Enrollment).filter(
        Enrollment.institution_id == course.institution_id,
        Enrollment.course_id == course.id,
        Enrollment.deleted_at.is_(None),
        Enrollment.status.in_(["active", "completed"]),
    ).all()
    registered_student_ids = {enrollment.student_id for enrollment in enrollments}

    matricules = set()
    if registered_student_ids:
        student_rows = db.query(Student).filter(
            Student.institution_id == course.institution_id,
            Student.id.in_(registered_student_ids),
            Student.deleted_at.is_(None),
        ).all()
        matricules = {str(student.student_id) for student in student_rows if student.student_id}

    if matricules:
        records = db.query(StudentRecord).filter(
            StudentRecord.institution_id == course.institution_id,
            StudentRecord.deleted_at.is_(None),
            func.lower(StudentRecord.course_code) == func.lower(course.code),
            StudentRecord.student_id.in_(matricules),
        ).all()
    else:
        records = []

    records_by_student = {}
    for record in records:
        key = str(record.student_id)
        previous = records_by_student.get(key)
        if not previous or (record.updated_at or record.created_at) > (previous.updated_at or previous.created_at):
            records_by_student[key] = record

    passed_students = 0
    for record in records_by_student.values():
        grade = (record.letter_grade or "").upper().strip()
        score = Decimal(str(record.total_score or 0))
        if grade in PASSING_GRADES or score >= Decimal("60"):
            passed_students += 1

    schedule_items = [
        CourseSchedulePerformanceItem(
            id=schedule.id,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            room=schedule.room,
            instructor=schedule.instructor,
            hours=_duration_hours(schedule.start_time, schedule.end_time),
        )
        for schedule in schedules
    ]
    instructors = sorted({s.instructor for s in schedules if s.instructor})

    department_name = None
    if course.department_id:
        department = db.query(Department).filter(
            Department.id == course.department_id,
            Department.deleted_at.is_(None),
        ).first()
        department_name = department.name if department else None

    registered_count = len(registered_student_ids)
    exam_written_count = len(records_by_student)

    return CoursePerformanceResponse(
        id=course.id,
        institution_id=course.institution_id,
        code=course.code,
        name=course.name,
        department_id=course.department_id,
        department_name=department_name,
        semester=course.semester,
        start_date=course.start_date,
        expected_end_date=course.expected_end_date,
        instructors=instructors,
        expected_teaching_hours=expected_hours,
        elapsed_scheduled_hours=elapsed_hours,
        progress_percentage=progress,
        registered_students=registered_count,
        exam_written_students=exam_written_count,
        passed_students=passed_students,
        pass_rate_percentage=_percentage(passed_students, exam_written_count),
        exam_participation_percentage=_percentage(exam_written_count, registered_count),
        schedules=schedule_items,
    )


def list_course_performance(
    db: Session,
    institution_id: Optional[int],
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
) -> list[CoursePerformanceResponse]:
    query = db.query(Course).filter(Course.deleted_at.is_(None))
    if institution_id is not None:
        query = query.filter(Course.institution_id == institution_id)
    if department_id:
        query = query.filter(Course.department_id == department_id)
    if semester:
        query = query.filter(Course.semester == semester)
    return [build_course_performance(db, course) for course in query.order_by(Course.code.asc()).all()]
